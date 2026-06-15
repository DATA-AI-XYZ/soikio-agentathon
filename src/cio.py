"""cio.py — adjudicator: deterministic Kintsugi scorer + CIO narrative (EPIC-02 FEAT-02.3).

Agents *classify*; this code *scores*. Severity, robustness and confidence are computed
from typed facts per docs/scoring.md — not free-text LLM judgement. The narrative + the
'what would resolve it' lines are the only LLM part, and they cannot change the verdict.
"""
from __future__ import annotations
import os, json, re
import llm

_P = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SYSTEM = open(os.path.join(_P, "prompts", "system.md"), encoding="utf-8").read()
CIO_PROMPT = open(os.path.join(_P, "prompts", "cio.md"), encoding="utf-8").read()
_ORDER = {"high": 0, "medium": 1, "low": 2}


def _severity(crack_type: str, load_bearing: bool, ncites: int) -> str:
    if crack_type == "contradicted":
        sev = "high" if load_bearing else "medium"
        if sev == "high" and ncites < 2:      # single-source cap (docs/scoring.md §1)
            sev = "medium"
        return sev
    if crack_type in ("unsupported", "vulnerable"):
        return "medium" if load_bearing else "low"
    return "low"


def build_conflict_map(claims: list[dict], cracks: list[dict]) -> list[dict]:
    lb = {c["id"]: bool(c.get("load_bearing")) for c in claims}
    merged: dict = {}
    for c in cracks:
        ct, cid = c.get("crack_type"), c.get("claim_id")
        if ct not in ("contradicted", "unsupported", "vulnerable"):
            continue
        if ct == "vulnerable" and not c.get("citations"):   # speculation rejected
            continue
        m = merged.setdefault((cid, ct), {"claim_id": cid, "crack_type": ct,
                                          "points": [], "citations": set(), "lenses": set(), "stances": set()})
        m["points"].append(c.get("point", ""))
        m["citations"].update(c.get("citations") or [])
        if c.get("lens"):
            m["lenses"].add(c["lens"])
        if c.get("stance"):
            m["stances"].add(c["stance"])
    out = []
    for (cid, ct), m in merged.items():
        out.append({
            "claim_id": cid, "crack_type": ct,
            "severity": _severity(ct, lb.get(cid, False), len(m["citations"])),
            "point": m["points"][0], "merged_from": m["points"][1:],
            "citations": sorted(m["citations"]), "lenses": sorted(m["lenses"]),
            "stances": sorted(m["stances"]), "what_would_resolve_it": "",
        })
    out.sort(key=lambda x: (_ORDER[x["severity"]], -len(x["citations"]), x["claim_id"]))
    return out


def _quote(content: str, n: int = 240) -> str:
    """A short, whitespace-normalised quote from a source chunk for the citation object."""
    q = " ".join((content or "").split())
    return (q[:n].rstrip() + "…") if len(q) > n else q


def enrich_conflict_map(cmap: list[dict], claims: list[dict], sources: list[dict]) -> list[dict]:
    """Align the conflict map to docs/output-schema.md (the shape the renderer expects).

    build_conflict_map keys cracks by `claim_id` and carries bare Sx citation ids; the schema +
    frontend want `claim_under_test` (the claim text) and citation OBJECTS {source_id, quote,
    locator}. This stamps both, looking the claim text up by claim_id and expanding each Sx id from
    the gathered `sources` bundle. `claim_id` is kept. Mutates + returns cmap (no LLM)."""
    claim_text = {c.get("id"): c.get("claim", "") for c in claims}
    src_by_id = {s.get("id"): s for s in (sources or [])}
    for c in cmap:
        c["claim_under_test"] = claim_text.get(c.get("claim_id"), "")
        c["citations"] = [
            {"source_id": sid,
             "quote": _quote(src_by_id[sid]["content"]) if sid in src_by_id else "",
             "locator": "doc-level"}
            for sid in (c.get("citations") or [])
        ]
    return cmap


def robustness(claims: list[dict], cmap: list[dict]) -> str:
    lb = {c["id"]: bool(c.get("load_bearing")) for c in claims}
    high_lb = any(c["severity"] == "high" and lb.get(c["claim_id"]) for c in cmap)
    unsup_lb = any(c["crack_type"] == "unsupported" and lb.get(c["claim_id"]) for c in cmap)
    med_lb = any(c["severity"] == "medium" and lb.get(c["claim_id"]) for c in cmap)
    med_all = sum(1 for c in cmap if c["severity"] == "medium")
    if high_lb or unsup_lb:
        return "Breaks"
    if med_lb or med_all >= 2:
        return "Contested"
    return "Holds"


def confidence(cmap: list[dict], data_completeness: float, base: float = 0.7,
               zero_evidence_load_bearing: bool = False, robustness: str | None = None) -> float:
    """Confidence with the documented caps (docs/scoring.md §3), applied in order."""
    conf = base
    if data_completeness < 0.5:
        conf = min(conf, 0.5)
    if robustness == "Breaks":                    # a broken thesis can't also read high-confidence
        conf = min(conf, 0.5)
    if any(c["severity"] == "high" for c in cmap):
        conf = min(conf, 0.45)
    if zero_evidence_load_bearing:                # a load-bearing claim with 0 evidence either way
        conf = min(conf, 0.4)
    return round(conf, 2)


def data_completeness(usable_lenses: int, active_lens_count: int) -> float:
    """lenses_with_usable_evidence / active_lens_count (docs/scoring.md §3). The denominator is the
    ACTIVE lens set actually run (3 for the MVP set, 6 for the full set) — never a hardcoded 6, so a
    3-lens MVP run is not penalised for lenses it never ran."""
    return round(usable_lenses / max(active_lens_count, 1), 2)


def stance_weights(points: list[dict], floor: float = 0.05) -> dict[str, float]:
    """Evidence-proportional stance weights, computed in code (ADR-0009): weight(s) =
    (cited_points(s) + FLOOR) / Σ (cited_points + FLOOR), summing to 1.0. Only points that
    survive the citation gate (have ≥1 citation) count. When all counts are zero the floor
    formula yields equal 1/3 weights — the documented fallback. Deterministic, no LLM."""
    counts = {"bull": 0, "bear": 0, "caution": 0}
    for p in points or []:
        st = p.get("stance")
        if st in counts and p.get("citations"):
            counts[st] += 1
    denom = sum(c + floor for c in counts.values())
    return {s: round((c + floor) / denom, 4) for s, c in counts.items()}


# Generic, non-falsifiable resolutions are rejected (docs/scoring.md §5) — they name no document/observation.
_GENERIC = re.compile(
    r"^(more|further|additional|better)\s+(disclosure|detail|information|transparency|data)\.?$"
    r"|^(next|future)\s+earnings(\s+release)?\.?$|^(wait and see|tbd|n/?a)\.?$", re.I)


def _is_generic(resolution: str) -> bool:
    """True if a resolution is too vague to be falsifiable (no specific document/event + observation)."""
    r = (resolution or "").strip()
    return len(r) < 25 or bool(_GENERIC.match(r))


def brief_fields(claims: list[dict], all_points: list[dict], cmap: list[dict],
                 data_completeness_value: float, equity_lean: str = "Caution",
                 zero_evidence_load_bearing: bool = False) -> dict:
    """Assemble the deterministic brief header — the scorer's outputs the renderer displays.
    `equity_lean` is the only LLM-derived field (passed in from narrate); the rest are code."""
    return {
        "weighed_stances": stance_weights(all_points),
        "thesis_robustness": robustness(claims, cmap),
        "equity_lean": equity_lean,
        "confidence": confidence(cmap, data_completeness_value,
                                 zero_evidence_load_bearing=zero_evidence_load_bearing),
    }


def narrate(thesis, extracted, cmap, support, verdict, conf):
    """LLM writes the brief + concrete 'what would resolve it' per crack. Cannot change the verdict.
    Generic (non-falsifiable) resolutions are rejected and regenerated to a claim-specific form."""
    user = (
        f"THESIS:\n{thesis}\n\nVERDICT (computed deterministically — do NOT change it): "
        f"{verdict} (confidence {conf}).\n\nCONFLICT MAP (ranked cracks):\n{json.dumps(cmap, indent=2)}\n\n"
        f"BULL SUPPORT:\n{json.dumps(support, indent=2)}\n\n"
        'Return JSON: {"brief":"3-5 sentences, every figure cited by its Sx id, NO BUY/SELL/HOLD",'
        '"equity_lean":"Bullish|Caution|Bearish",'
        '"resolutions":["for crack #1: a specific document/event AND the observation that would flip it","#2 ..."]}'
    )
    try:
        data = llm.json_chat(SYSTEM + "\n\n" + CIO_PROMPT, user, model=llm.CIO_MODEL, max_tokens=2000)
    except Exception:
        data = {}
    res = data.get("resolutions", []) if isinstance(data, dict) else []
    for i, c in enumerate(cmap):
        r = res[i] if i < len(res) else ""
        if _is_generic(r):  # reject + regenerate to a concrete, claim-specific resolution
            r = (f"A specific filing or dated disclosure for claim {c['claim_id']} whose stated figure "
                 f"would flip this '{c['crack_type']}' crack on the {', '.join(c.get('lenses') or []) or 'relevant'} lens.")
        c["what_would_resolve_it"] = r
    return data.get("brief", ""), data.get("equity_lean", "Caution")
