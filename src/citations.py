"""citations.py — the reliability moat (EPIC-03). The whole product's audit-grade claim lives here.

Gates (reliability-spec.md):
- compliance (§3): a transact instruction (rating / recommendation / imperative action / framed
  price target) is blocked — without false-positiving descriptive vocabulary.
- faithfulness (§1): every figure is machine-checked against its citation quote, and every quote
  against the actual retrieved extract. Fabricated quote → reject the crack; unverifiable figure →
  strip the figure (cite-or-silence). A doc-level-only locator caps crack severity at medium.
- attack-bias (§4): cited-contradicted vs uncited-vulnerable disclosure; an all-vulnerable map is
  flagged low-conviction.

The coverage classifier (§2, unsupported vs data_gap) lives alongside in `coverage_gate`.
"""
from __future__ import annotations
import re

# Block the BUY/SELL/HOLD *instruction*, not every occurrence of the words (R7, reliability-spec §3).
# Match advisory INTENT, never substrings: allow "claims hold", "holds", "sell-side consensus",
# "buyback", "holding period", "buyers returned", "the bull case" — they describe, not instruct.
_CAPS = re.compile(r"\b(BUY|SELL|HOLD)\b")  # case-sensitive: the rating convention (a rating IS advice)
_INTENT = re.compile(
    r"\b(?:recommend(?:ed|ation)?|rate[ds]?|rating(?:\s+of)?|issue[ds]?\s+a|should)\s+"
    r"(?:(?:a|an|strong|the)\s+)*(buy|sell|hold)\b", re.I)
# Imperative transact actions on the security (reliability-spec §3): the verb + a position/security object.
_ACTION = re.compile(
    r"\b(?:buy|sell|accumulate|short|long)\s+"
    r"(?:the\s+|its\s+|this\s+|your\s+|more\s+)?(?:stock|shares|equity|position|name|security)\b", re.I)
# Bare imperative transact phrases that are advice on their own (no object needed).
_IMPERATIVE = re.compile(
    r"\b(?:take\s+profits?|trim\s+(?:the\s+|your\s+)?(?:position|stake|holding)|"
    r"go\s+(?:long|short)|add\s+to\s+(?:the\s+|your\s+)?position|exit\s+(?:the\s+|your\s+)?(?:position|stock|name)|"
    r"(?:buy|sell|accumulate)\s+(?:now|here|today))\b", re.I)
# A price target framed as an instruction ("target $200, buy" / "buy with a $200 target").
_TARGET = re.compile(
    r"(?:\b(?:buy|sell)\b[^.]{0,40}\bprice\s+target\b)|(?:\bprice\s+target\b[^.]{0,40}\b(?:buy|sell)\b)", re.I)


def block_advice(text: str) -> bool:
    """True only if the text gives a transact *instruction* (rating / recommendation / imperative action /
    instruction-framed price target). Matches advisory intent, not substrings (reliability-spec §3)."""
    t = text or ""
    return bool(_CAPS.search(t) or _INTENT.search(t) or _ACTION.search(t)
                or _IMPERATIVE.search(t) or _TARGET.search(t))


# --- faithfulness gate (reliability-spec §1) --------------------------------------------
_MATERIAL = ("contradicted", "vulnerable", "support")
_SEV = {"high": 0, "medium": 1, "low": 2}
_DOC_LEVEL = {"", "doc-level", "doc", "document", "doc level"}
# A figure: optional $, digits with optional thousands-separators/decimals, optional unit.
_FIG = re.compile(r"\$?\d[\d,]*(?:\.\d+)?\s*(?:billion|million|bps|bn|b|m|k|%)?", re.I)


def _norm(s: str) -> str:
    """Normalise for brittle-proof substring matching: lowercase, drop thousands commas, tighten %/space."""
    s = (s or "").lower()
    s = re.sub(r"(?<=\d),(?=\d)", "", s)   # 1,000 -> 1000
    s = re.sub(r"\s*%", "%", s)            # 44 % -> 44%
    return re.sub(r"\s+", " ", s).strip()


def _figures(text: str) -> list[str]:
    """Original figure substrings present in prose (kept verbatim so they can be stripped in place)."""
    return [m.strip() for m in _FIG.findall(text or "") if re.search(r"\d", m)]


def _is_doc_level(locator: str | None) -> bool:
    """True iff the locator is only a doc-level reference (can't pinpoint → severity capped)."""
    return (locator or "").strip().lower() in _DOC_LEVEL and (locator or "").strip().lower() != ""


def cap_severity(severity: str, locator: str | None) -> str:
    """Cap a crack's severity at medium when it can only be pinned to a doc-level locator (§1.3)."""
    if _is_doc_level(locator) and _SEV.get(severity, 2) < _SEV["medium"]:
        return "medium"
    return severity


def faithful(points: list[dict], source_ids: set[str],
             extracts: dict[str, str] | None = None) -> list[dict]:
    """The anti-fabrication core (reliability-spec §1).

    Always: drop citations not mapping to a real source; silence a material point left uncited.

    With `extracts` ({source_id: retrieved_text}) the machine-checks fire per point that carries a
    `quote`:
      - quote-in-extract (§1.2): the quote must be a substring of a cited extract, else the point is
        a fabricated citation and is REJECTED entirely (a contradicted crack is suppressed ONLY here).
      - quote-contains-figure (§1.1): a figure in the prose absent from the quote is STRIPPED and the
        claim flagged (`figure_flagged`); the point survives if it keeps valid cited support.
      - locator (§1.3): a doc-level-only locator annotates `severity_cap="medium"` for the map.

    `extracts=None` keeps the original (back-compatible) behaviour — id-validity + cite-or-silence only."""
    out: list[dict] = []
    for p in points:
        p["citations"] = [c for c in (p.get("citations") or []) if c in source_ids]
        ct = p.get("crack_type")

        if extracts is not None and p.get("quote"):
            qn = _norm(p["quote"])
            cited_text = " ".join(_norm(extracts.get(c, "")) for c in p["citations"])
            if not qn or qn not in cited_text:
                continue  # quote not in any retrieved extract → fabricated citation → reject (E9, §1.2)
            stripped = [f for f in _figures(p.get("point", "")) if _norm(f) not in qn]
            if stripped:                                   # unverifiable figure → strip + flag (E6, §1.1)
                display = p.get("point", "")
                for f in stripped:
                    display = display.replace(f, "[figure unverified]")
                p["point"], p["figure_flagged"], p["stripped_figures"] = display, True, stripped
            if _is_doc_level(p.get("locator")):
                p["severity_cap"] = "medium"               # §1.3 — carried to the conflict map

        if ct in _MATERIAL and not p["citations"]:
            continue  # material claim with no faithful source → silence it (cite-or-silence)
        out.append(p)
    return out


def attack_bias(cracks: list[dict]) -> dict:
    """Disclosure of the Bear's contrarian bias (reliability-spec §4): cited-`contradicted` vs
    uncited-`vulnerable`. A crack set that is all-`vulnerable` with no `contradicted` is flagged
    `low_conviction` (the Bear is reaching). `ratio` is cited-contradicted / uncited-vulnerable."""
    cited_contradicted = sum(1 for c in cracks if c.get("crack_type") == "contradicted" and c.get("citations"))
    uncited_vulnerable = sum(1 for c in cracks if c.get("crack_type") == "vulnerable" and not c.get("citations"))
    n_contradicted = sum(1 for c in cracks if c.get("crack_type") == "contradicted")
    n_vulnerable = sum(1 for c in cracks if c.get("crack_type") == "vulnerable")
    return {
        "cited_contradicted": cited_contradicted,
        "uncited_vulnerable": uncited_vulnerable,
        "contradicted": n_contradicted,
        "vulnerable": n_vulnerable,
        "ratio": round(cited_contradicted / uncited_vulnerable, 2) if uncited_vulnerable else None,
        "low_conviction": n_contradicted == 0 and n_vulnerable > 0,
    }


# --- coverage gate (reliability-spec §2) -------------------------------------------------
def coverage_gate(cracks: list[dict], coverage_fn=None) -> tuple[list[dict], int]:
    """Tell "the corpus lacks the page" apart from "the claim is baseless" (reliability-spec §2).

    Before an `unsupported` crack is admitted, probe whether the knowledge base covers the claim/lens
    at all, via the FROZEN `foundry_iq.coverage(claim, lens)` (ADR-0015):
      - coverage present, no supporting evidence → it stays a legitimate `unsupported` crack;
      - NO coverage → relabel `crack_type` to `data_gap`. A `data_gap` is off-map by construction —
        `cio.build_conflict_map` only admits contradicted/unsupported/vulnerable — so it never shows
        as a flaw in the user's thesis; instead the returned count lowers `data_completeness`.

    Non-`unsupported` cracks pass through untouched. Returns `(cracks, data_gap_count)`.
    `coverage_fn` defaults to the live/mock `foundry_iq.coverage` (lazy-imported so `citations`
    stays import-light); tests inject a stub."""
    if coverage_fn is None:
        import foundry_iq
        coverage_fn = foundry_iq.coverage
    out: list[dict] = []
    gaps = 0
    for c in cracks:
        if c.get("crack_type") == "unsupported":
            probe = c.get("point") or c.get("claim_id") or ""
            if not coverage_fn(probe, c.get("lens")):
                c = {**c, "crack_type": "data_gap"}   # off-map; lowers completeness, not a crack
                gaps += 1
        out.append(c)
    return out, gaps
