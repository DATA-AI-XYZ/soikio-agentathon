#!/usr/bin/env python3
"""run_evals.py — the behavioural eval suite (EPIC-05 FEAT-05.1 / STORY-05.1.01).

Runs the nine demoable reliability checks from docs/evaluation.md and writes a machine-readable
evidence artefact the README / demo can quote. Honest by construction:

  - E1, E4, E5 read the SAVED LIVE RUN (out/saved-run.json) — real Foundry IQ retrieval, real agents.
  - E2, E3, E6, E7, E8, E9 exercise the DETERMINISTIC reliability gates (citations.* + the cio scorer)
    on controlled fixtures — zero LLM, zero Azure, fully reproducible. This is what makes the suite
    deterministic (the user's requirement) and is faithful to the gates' actual contracts: the gates
    are pure functions, so proving them on crafted inputs proves the behaviour the live path relies on.

Each eval returns pass/fail + the documented assertion + a small evidence detail block.

Usage:
  python scripts/run_evals.py --evals E1,E2,E3,E4,E5,E6,E7,E8,E9     # full suite
  python scripts/run_evals.py --evals E8 --repeat 3                  # determinism, 3x
Exit code is 0 only if every requested eval passes (so `&& echo EVALS_OK` gates on green).
"""
from __future__ import annotations
import os, sys, json, re, argparse

_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(_ROOT, "src"))

# The mock retrieval backend is selected for any live-ish probe (none here call Azure, but keep the
# offline contract explicit and self-documenting). Set before importing the gates.
os.environ.setdefault("FOUNDRY_IQ_BACKEND", "mock")

import citations  # noqa: E402  — the reliability moat (pure functions; no LLM at import)
import cio        # noqa: E402  — deterministic Kintsugi scorer

# LLM crack prose carries Unicode (→, em dashes); the Windows cp1252 console crashes on print
# (BUG-20260614-01). Force UTF-8 so the evidence prints everywhere.
for _stream in (sys.stdout, sys.stderr):
    try:
        _stream.reconfigure(encoding="utf-8", errors="replace")
    except (AttributeError, ValueError):
        pass

SAVED_RUN = os.path.join(_ROOT, "out", "saved-run.json")
COMPLIANCE_FIXTURE = os.path.join(_ROOT, "tests", "fixtures", "compliance_allow_deny.json")
OUT_RESULTS = os.path.join(_ROOT, "out", "eval-results.json")
EVALS_DIR = os.path.join(_ROOT, "evals")

# A figure token in prose (mirrors citations._FIG): optional $, digits, optional unit.
_FIG = re.compile(r"\$?\d[\d,]*(?:\.\d+)?\s*(?:billion|million|bps|bn|b|m|k|x|%)?", re.I)
_SRCREF = re.compile(r"\bS\d+\b")          # an Sx source citation inside the brief prose
_CLAIMREF = re.compile(r"\bc\d+\b")        # a claim id like c1/c2 — NOT a figure
_SENT_SPLIT = re.compile(r"(?<=[.!?])\s+(?=[A-Z'\"(])")


def _load_saved_run() -> dict:
    with open(SAVED_RUN, encoding="utf-8") as f:
        return json.load(f)


def _figures(text: str) -> list[str]:
    """Figures in prose, with claim ids (c1, c2…) removed first so they are not mistaken for numbers."""
    cleaned = _CLAIMREF.sub("", text or "")
    return [m.strip() for m in _FIG.findall(cleaned) if re.search(r"\d", m)]


# --------------------------------------------------------------------------------------------------
# E1 — Normal run (saved live run): a robustness verdict + confidence + >=1 cited crack.
# --------------------------------------------------------------------------------------------------
def eval_e1() -> dict:
    brief = _load_saved_run()
    verdict = brief.get("thesis_robustness")
    conf = brief.get("confidence")
    cited_cracks = [c for c in brief.get("conflict_map", []) if c.get("citations")]
    ok = (verdict in ("Holds", "Contested", "Breaks")
          and isinstance(conf, (int, float))
          and len(cited_cracks) >= 1)
    return {
        "id": "E1", "name": "Normal run (baseline end-to-end)", "passed": ok,
        "assertion": "saved live run yields a Holds/Contested/Breaks verdict with confidence and >=1 cited crack",
        "detail": {"verdict": verdict, "confidence": conf,
                   "cited_cracks": len(cited_cracks), "total_cracks": len(brief.get("conflict_map", []))},
        "source": "out/saved-run.json",
    }


# --------------------------------------------------------------------------------------------------
# E2 — Missing-evidence probe (MANDATORY): a thesis claim about a metric absent from the KB must
# (a) be silenced if material-but-uncited (cite-or-silence) and (b) relabel unsupported -> data_gap
# (lowering data_completeness), and (c) NO invented number survives. Proves the gates.
# --------------------------------------------------------------------------------------------------
def eval_e2() -> dict:
    # (a) cite-or-silence: a material (contradicted) point with no faithful citation is dropped,
    #     never echoed with an invented figure.
    fabricated = [{"crack_type": "contradicted", "claim_id": "c9", "lens": "valuation",
                   "point": "Free cash flow margin collapsed to 12% last quarter.",  # invented number
                   "citations": []}]
    silenced = citations.faithful(fabricated, source_ids={"S1", "S2"})
    cite_or_silence_ok = len(silenced) == 0  # uncited material claim removed -> no invented number ships

    # (b) coverage gate: an unsupported crack the corpus cannot cover becomes an off-map data_gap.
    unsupported = [{"crack_type": "unsupported", "claim_id": "c9", "lens": "valuation",
                    "point": "Free cash flow margin trend for the missing metric."}]
    relabelled, gaps = citations.coverage_gate(unsupported, coverage_fn=lambda claim, lens: False)
    relabel_ok = gaps == 1 and relabelled[0]["crack_type"] == "data_gap"

    # data_gap is off-map by construction (build_conflict_map admits only contradicted/unsupported/vulnerable)
    cmap = cio.build_conflict_map([{"id": "c9", "load_bearing": True}], relabelled)
    off_map_ok = len(cmap) == 0

    # (c) lowered confidence when completeness drops below the 0.5 cap.
    conf_full = cio.confidence([], data_completeness=1.0)
    conf_gap = cio.confidence([], data_completeness=0.3)
    lowered_ok = conf_gap < conf_full

    ok = cite_or_silence_ok and relabel_ok and off_map_ok and lowered_ok
    return {
        "id": "E2", "name": "Missing-evidence probe (cite-or-silence)", "passed": ok, "mandatory": True,
        "assertion": "absent-metric claim is silenced (no invented number), relabelled unsupported->data_gap "
                     "(off-map), and confidence is lowered",
        "detail": {"cite_or_silence_dropped": cite_or_silence_ok, "data_gaps": gaps,
                   "relabelled_to": relabelled[0]["crack_type"], "off_map": off_map_ok,
                   "confidence_full": conf_full, "confidence_with_gap": conf_gap},
        "source": "deterministic gate (citations.faithful + coverage_gate + cio.confidence)",
    }


# --------------------------------------------------------------------------------------------------
# E3 — No-advice probe: transact instructions blocked, descriptive vocabulary flows; the saved
# brief carries no BUY/SELL/HOLD. Proves the compliance guard (reliability-spec §3).
# --------------------------------------------------------------------------------------------------
def eval_e3() -> dict:
    with open(COMPLIANCE_FIXTURE, encoding="utf-8") as f:
        fx = json.load(f)
    deny_blocked = [t for t in fx["deny"] if citations.block_advice(t)]
    allow_passed = [t for t in fx["allow"] if not citations.block_advice(t)]
    deny_ok = len(deny_blocked) == len(fx["deny"])      # every transact instruction blocked
    allow_ok = len(allow_passed) == len(fx["allow"])    # no descriptive phrase false-positived

    brief = _load_saved_run()
    saved_compliance_ok = brief.get("compliance_ok") is True and not citations.block_advice(brief.get("brief", ""))

    ok = deny_ok and allow_ok and saved_compliance_ok
    return {
        "id": "E3", "name": "No-advice probe (compliance guard)", "passed": ok,
        "assertion": "all transact instructions blocked, all descriptive phrases allowed, saved brief emits no BUY/SELL/HOLD",
        "detail": {"deny_blocked": f"{len(deny_blocked)}/{len(fx['deny'])}",
                   "allow_passed": f"{len(allow_passed)}/{len(fx['allow'])}",
                   "saved_brief_compliance_ok": saved_compliance_ok},
        "source": "tests/fixtures/compliance_allow_deny.json + out/saved-run.json",
    }


# --------------------------------------------------------------------------------------------------
# E4 — Crack surfacing (Kintsugi): saved conflict_map is non-empty, ranked by severity, confidence
# capped. Proves conflict-as-signal (STORY-02.3.01).
# --------------------------------------------------------------------------------------------------
def eval_e4() -> dict:
    brief = _load_saved_run()
    cmap = brief.get("conflict_map", [])
    order = {"high": 0, "medium": 1, "low": 2}
    sevs = [order.get(c.get("severity"), 3) for c in cmap]
    ranked_ok = sevs == sorted(sevs)                       # ranked by severity (high -> low)
    has_high = any(c.get("severity") == "high" for c in cmap)
    capped_ok = (brief.get("confidence", 1.0) <= 0.45) if has_high else True
    ok = len(cmap) >= 1 and ranked_ok and capped_ok
    return {
        "id": "E4", "name": "Crack surfacing (conflict-as-signal)", "passed": ok,
        "assertion": "conflict_map is non-empty, ranked by severity, and confidence is capped when a high-severity crack exists",
        "detail": {"cracks": len(cmap), "ranked_by_severity": ranked_ok,
                   "has_high_severity": has_high, "confidence": brief.get("confidence")},
        "source": "out/saved-run.json",
    }


# --------------------------------------------------------------------------------------------------
# E5 — Citation integrity: every figure in the narrative is cited; every cited Sx exists. Proves
# grounding (STORY-04.1.01).
# --------------------------------------------------------------------------------------------------
def eval_e5() -> dict:
    brief = _load_saved_run()
    prose = brief.get("brief", "")
    source_ids = {s["id"] for s in brief.get("sources", [])}
    refs = set(_SRCREF.findall(prose))
    dangling = sorted(r for r in refs if r not in source_ids)       # citations pointing nowhere
    uncited_fig_sentences = []
    for sent in _SENT_SPLIT.split(prose):
        if _figures(sent) and not _SRCREF.search(sent):
            uncited_fig_sentences.append(sent.strip()[:90])
    ok = not dangling and not uncited_fig_sentences
    return {
        "id": "E5", "name": "Citation integrity (grounding)", "passed": ok,
        "assertion": "every figure-bearing sentence carries an Sx citation and every Sx resolves to a real source",
        "detail": {"sources": len(source_ids), "refs_in_brief": sorted(refs),
                   "dangling_refs": dangling, "uncited_figure_sentences": uncited_fig_sentences},
        "source": "out/saved-run.json",
    }


# --------------------------------------------------------------------------------------------------
# E6 — Faithfulness: a thesis figure absent from the cited extract is stripped + flagged, the crack
# survives on its valid support. Proves the faithfulness gate (reliability-spec §1.1).
# --------------------------------------------------------------------------------------------------
def eval_e6() -> dict:
    extract_text = "China revenue declined materially year over year per the 10-K."  # no figure here
    point = [{"crack_type": "contradicted", "claim_id": "c3", "lens": "macro",
              "point": "China revenue declined to $19.7 billion, contradicting continued access.",
              "quote": "China revenue declined materially year over year per the 10-K.",
              "citations": ["S8"], "locator": "p.42"}]
    out = citations.faithful([dict(p) for p in point], source_ids={"S8"}, extracts={"S8": extract_text})
    survived = len(out) == 1
    flagged = survived and out[0].get("figure_flagged") is True
    stripped = survived and "$19.7 billion" in (out[0].get("stripped_figures") or [])
    masked = survived and "[figure unverified]" in out[0].get("point", "")
    ok = survived and flagged and stripped and masked
    return {
        "id": "E6", "name": "Faithfulness (strip unverifiable figure)", "passed": ok,
        "assertion": "a figure absent from the cited extract is stripped + flagged while the crack survives on valid support",
        "detail": {"crack_survived": survived, "figure_flagged": flagged,
                   "stripped_figures": out[0].get("stripped_figures") if survived else None,
                   "point_after": out[0].get("point") if survived else None},
        "source": "deterministic gate (citations.faithful with extracts)",
    }


# --------------------------------------------------------------------------------------------------
# E7 — Coverage: a claim with no covering document returns a data_gap, NOT an unsupported crack.
# Proves the coverage probe (reliability-spec §2).
# --------------------------------------------------------------------------------------------------
def eval_e7() -> dict:
    cracks = [
        {"crack_type": "unsupported", "claim_id": "c5", "lens": "valuation",
         "point": "Valuation justified by forward multiples the corpus never covers."},
        {"crack_type": "unsupported", "claim_id": "c2", "lens": "competition",
         "point": "No credible competition — a claim the corpus DOES cover but cannot support."},
    ]
    # corpus covers the competition claim (c2) but not the valuation claim (c5).
    covers = lambda claim, lens: lens == "competition"
    out, gaps = citations.coverage_gate([dict(c) for c in cracks], coverage_fn=covers)
    by_claim = {c["claim_id"]: c["crack_type"] for c in out}
    gap_ok = by_claim.get("c5") == "data_gap"               # uncovered -> data_gap
    unsupported_ok = by_claim.get("c2") == "unsupported"    # covered-but-unevidenced stays unsupported
    ok = gaps == 1 and gap_ok and unsupported_ok
    return {
        "id": "E7", "name": "Coverage (data_gap vs unsupported)", "passed": ok,
        "assertion": "an uncovered claim becomes a data_gap (off-map) while a covered-but-unevidenced claim stays unsupported",
        "detail": {"data_gaps": gaps, "c5_uncovered": by_claim.get("c5"), "c2_covered": by_claim.get("c2")},
        "source": "deterministic gate (citations.coverage_gate)",
    }


# --------------------------------------------------------------------------------------------------
# E8 — Determinism: scoring the same typed facts N times yields identical robustness + identical
# high-severity crack set. Proves the derived scorer (docs/scoring.md). --repeat controls N.
# --------------------------------------------------------------------------------------------------
def _score_once() -> tuple[str, tuple]:
    claims = [{"id": "c3", "load_bearing": True}, {"id": "c1", "load_bearing": True},
              {"id": "c5", "load_bearing": False}]
    cracks = [
        {"crack_type": "contradicted", "claim_id": "c3", "lens": "macro",
         "point": "China access contradicted.", "citations": ["S8", "S9"]},
        {"crack_type": "unsupported", "claim_id": "c5", "lens": "valuation",
         "point": "Valuation unsupported.", "citations": ["S15"]},
        {"crack_type": "vulnerable", "claim_id": "c1", "lens": "competition",
         "point": "Competition exposure.", "citations": ["S7"]},
    ]
    cmap = cio.build_conflict_map(claims, cracks)
    verdict = cio.robustness(claims, cmap)
    high = tuple(sorted((c["claim_id"], c["crack_type"]) for c in cmap if c["severity"] == "high"))
    return verdict, high


def eval_e8(repeat: int = 3) -> dict:
    runs = [_score_once() for _ in range(max(repeat, 2))]
    verdicts = {r[0] for r in runs}
    high_sets = {r[1] for r in runs}
    ok = len(verdicts) == 1 and len(high_sets) == 1
    return {
        "id": "E8", "name": "Determinism (derived scoring)", "passed": ok,
        "assertion": f"{len(runs)} identical-input runs produce one robustness verdict and one high-severity crack set",
        "detail": {"runs": len(runs), "verdict": runs[0][0], "distinct_verdicts": len(verdicts),
                   "high_severity_cracks": [list(t) for t in runs[0][1]], "distinct_high_sets": len(high_sets)},
        "source": "deterministic scorer (cio.build_conflict_map + robustness)",
    }


# --------------------------------------------------------------------------------------------------
# E9 — Anti-fabrication: a crack whose quote appears in NO retrieved extract is rejected entirely.
# Proves the anti-fabrication core (reliability-spec §1.2).
# --------------------------------------------------------------------------------------------------
def eval_e9() -> dict:
    real_extract = "NVIDIA is already effectively foreclosed from the China market by U.S. export controls."
    points = [
        {"crack_type": "contradicted", "claim_id": "c3", "lens": "macro",
         "point": "Foreclosed from China.", "citations": ["S8"],
         "quote": "NVIDIA is already effectively foreclosed from the China market by U.S. export controls."},
        {"crack_type": "contradicted", "claim_id": "c7", "lens": "macro",
         "point": "Fabricated: management admitted bankruptcy risk.", "citations": ["S8"],
         "quote": "Management privately admitted the company faces imminent bankruptcy."},  # not in extract
    ]
    out = citations.faithful([dict(p) for p in points], source_ids={"S8"}, extracts={"S8": real_extract})
    kept_quotes = [p.get("quote", "")[:40] for p in out]
    real_kept = any("effectively foreclosed" in q for q in kept_quotes)
    fabricated_rejected = not any("imminent bankruptcy" in q for q in kept_quotes)
    ok = len(out) == 1 and real_kept and fabricated_rejected
    return {
        "id": "E9", "name": "Anti-fabrication (reject fabricated quote)", "passed": ok,
        "assertion": "a crack whose quote is absent from every retrieved extract is rejected; the genuine crack survives",
        "detail": {"input_cracks": 2, "surviving_cracks": len(out),
                   "fabricated_rejected": fabricated_rejected, "genuine_kept": real_kept},
        "source": "deterministic gate (citations.faithful with extracts)",
    }


EVALS = {
    "E1": eval_e1, "E2": eval_e2, "E3": eval_e3, "E4": eval_e4, "E5": eval_e5,
    "E6": eval_e6, "E7": eval_e7, "E8": eval_e8, "E9": eval_e9,
}


def _merge_results(new: list[dict]) -> list[dict]:
    """Merge into the canonical artefact by id (so a single-eval run doesn't clobber the full set)."""
    existing: dict = {}
    if os.path.exists(OUT_RESULTS):
        try:
            with open(OUT_RESULTS, encoding="utf-8") as f:
                for r in json.load(f).get("results", []):
                    existing[r["id"]] = r
        except (json.JSONDecodeError, OSError, KeyError):
            existing = {}
    for r in new:
        existing[r["id"]] = r
    return [existing[k] for k in sorted(existing)]


def _evidence_md(results: list[dict], passed: int, total: int) -> str:
    lines = ["# Eval evidence — STORY-05.1.01 (E1–E9)", "",
             f"**{passed}/{total} evals passed.** Generated by `scripts/run_evals.py`.", "",
             "E1/E4/E5 read the saved live run (`out/saved-run.json`); E2/E3/E6–E9 exercise the "
             "deterministic reliability gates on controlled fixtures (no LLM, fully reproducible).", "",
             "| Eval | Check | Result | Assertion |",
             "|------|-------|--------|-----------|"]
    for r in results:
        mark = "✅ PASS" if r["passed"] else "❌ FAIL"
        lines.append(f"| {r['id']} | {r['name']} | {mark} | {r['assertion']} |")
    lines += ["", "## Detail", "", "```json", json.dumps(results, indent=2), "```", ""]
    return "\n".join(lines)


def main() -> int:
    ap = argparse.ArgumentParser(description="Run the behavioural eval suite E1–E9.")
    ap.add_argument("--evals", default=",".join(EVALS),
                    help="comma-separated eval ids, e.g. E1,E2,...,E9 (default: all)")
    ap.add_argument("--repeat", type=int, default=3, help="repeat count for E8 determinism")
    a = ap.parse_args()

    requested = [e.strip().upper() for e in a.evals.split(",") if e.strip()]
    unknown = [e for e in requested if e not in EVALS]
    if unknown:
        print(f"error: unknown eval(s): {', '.join(unknown)} (valid: {', '.join(EVALS)})", file=sys.stderr)
        return 2

    results = []
    for eid in requested:
        fn = EVALS[eid]
        res = fn(a.repeat) if eid == "E8" else fn()
        results.append(res)
        mark = "PASS" if res["passed"] else "FAIL"
        print(f"[{mark}] {res['id']} · {res['name']}")
        print(f"        {res['assertion']}")
        print(f"        evidence: {json.dumps(res['detail'])}")

    merged = _merge_results(results)
    passed = sum(1 for r in merged if r["passed"])
    payload = {"suite": "behavioural-evals", "story": "STORY-05.1.01",
               "passed": passed, "total": len(merged), "results": merged}

    os.makedirs(os.path.dirname(OUT_RESULTS), exist_ok=True)
    with open(OUT_RESULTS, "w", encoding="utf-8") as f:
        json.dump(payload, f, indent=2)
    os.makedirs(EVALS_DIR, exist_ok=True)
    with open(os.path.join(EVALS_DIR, "eval-results.json"), "w", encoding="utf-8") as f:
        json.dump(payload, f, indent=2)
    with open(os.path.join(EVALS_DIR, "EVIDENCE.md"), "w", encoding="utf-8") as f:
        f.write(_evidence_md(merged, passed, len(merged)))

    run_passed = sum(1 for r in results if r["passed"])
    print(f"\n{run_passed}/{len(results)} requested eval(s) passed "
          f"({passed}/{len(merged)} recorded in out/eval-results.json).")
    return 0 if run_passed == len(results) else 1


if __name__ == "__main__":
    sys.exit(main())
