"""
reviewer.py — the Reviewer agent: historical comparison + feedback.

Runs AFTER the CIO. Compares the current brief to the entity's prior run and
emits a `review` block whose deltas are COMPUTED IN CODE (never the LLM), so the
narrative can't drift from the numbers.

Flow:  extract → domains → Bull/Bear/Caution → CIO → reviewer.run_review → render
                                                          │
                                                   reads memory (history)

Honesty contract (mirrors prompts/reviewer.md):
  • deltas are computed in code (not the LLM);
  • consistency / drift / recurring themes are measurable now;
  • PREDICTIVE calibration needs outcome labels — until those exist, status = "tracking".

The deterministic core (`compute_deltas`, `run_review`) runs fully OFFLINE: no store
and no LLM are required. A store (prior-run lookup) and an `ask_claude` narrative are
optional enrichments wired in by the live pipeline (STORY-09.4.03).
"""
from __future__ import annotations

import json
import pathlib
from typing import Callable, Optional, Union

_CAL_NOTE = (
    "Consistency, drift and recurring themes are measured from stored runs. "
    "Predictive calibration (were the high-severity cracks the ones that later broke "
    "the thesis?) requires outcome capture over time."
)


def _load(x: Union[dict, str, None]) -> Optional[dict]:
    """Accept a brief dict OR a path to a brief JSON file (or None)."""
    if x is None:
        return None
    if isinstance(x, dict):
        return x
    return json.loads(pathlib.Path(x).read_text(encoding="utf-8"))


def _verdict(brief: dict):
    return brief.get("thesis_robustness") or brief.get("verdict")


def _ticker(brief: dict) -> str:
    """Entity ticker, tolerant of shape (M1/M2): top-level entity dict/str, or thesis.entity."""
    e = brief.get("entity")
    if isinstance(e, dict):
        return e.get("ticker") or e.get("name") or ""
    if isinstance(e, str):
        return e
    th = brief.get("thesis")
    if isinstance(th, dict):
        ent = th.get("entity")
        return (ent.get("ticker", "") if isinstance(ent, dict) else th.get("ticker", "")) or ""
    return ""


def _crack_set(brief: dict) -> set:
    """Crack identity set. Accepts the simple `{cracks: [...]}` shape OR the real
    brief `{conflict_map: [{claim_under_test, crack_type}]}` shape."""
    cracks = brief.get("cracks")
    if isinstance(cracks, list):
        return {str(c) for c in cracks}
    out = set()
    for c in brief.get("conflict_map") or []:
        cut, ct = c.get("claim_under_test"), c.get("crack_type")
        if cut is None and ct is None:           # skip malformed/empty entries (M3)
            continue
        out.add(f"{cut} [{ct}]")
    return out


def compute_deltas(current: dict, prior: Optional[dict]) -> dict:
    """Deterministic crack / verdict / confidence deltas vs the prior run. No LLM."""
    cur = _crack_set(current)
    if not prior:
        return {"had_prior": False, "healed": [], "new": sorted(cur),
                "persisting": [], "verdict_delta": None, "confidence_delta": None}
    pri = _crack_set(prior)
    order = {"Holds": 2, "Contested": 1, "Breaks": 0}
    pv, cv = _verdict(prior), _verdict(current)
    verdict_delta = "unchanged"
    if pv in order and cv in order:
        verdict_delta = ("improved" if order[cv] > order[pv]
                         else "deteriorated" if order[cv] < order[pv] else "unchanged")
    run = prior.get("run") or {}
    return {
        "had_prior": True,
        "healed": sorted(pri - cur),         # in prior, gone now
        "new": sorted(cur - pri),            # appeared this run
        "persisting": sorted(cur & pri),     # still open
        "verdict_delta": verdict_delta,
        "prior_verdict": pv,
        "current_verdict": cv,
        "confidence_delta": round((current.get("confidence") or 0) - (prior.get("confidence") or 0), 3),
        "prior_run_id": run.get("id") or run.get("run_id"),   # id first (pipeline writes run["id"])
    }


def history_summary(store, ticker: str) -> dict:
    rows = store.list_runs(limit=500)
    mine = [r for r in rows if (r.get("ticker") or "").upper() == ticker.upper()]
    verdicts = [r.get("thesis_robustness") for r in rows if r.get("thesis_robustness")]
    return {
        "runs_considered": len(rows),
        "runs_this_entity": len(mine),
        "verdict_mix": {v: verdicts.count(v) for v in sorted(set(verdicts))},
    }


def run_review(
    current: Union[dict, str],
    prior: Union[dict, str, None] = None,
    store=None,
    ask_claude: Optional[Callable[[str, str], str]] = None,
    prompts_dir: str = "prompts",
) -> dict:
    """Build the `review` block. Deterministic + offline by default.

    `current`/`prior` may be a brief dict or a path to one. If `prior` is omitted but a
    `store` is given, the prior run is looked up by entity ticker. If `ask_claude` is
    given (live pipeline), an LLM narrative is added — but it can never change the
    code-computed deltas. Returns `{"review": {...}}` (output-schema `review`)."""
    cur = _load(current)
    pri = _load(prior)
    ticker = _ticker(cur)
    if pri is None and store is not None and ticker:
        pri = store.prior_run(ticker)

    deltas = compute_deltas(cur, pri)

    # `review` block per docs/output-schema.md (nested vs_prior_run with cracks_* names).
    review = {
        "vs_prior_run": {
            "had_prior": deltas["had_prior"],
            "prior_run_id": deltas.get("prior_run_id"),
            "prior_verdict": deltas.get("prior_verdict"),
            "current_verdict": deltas.get("current_verdict"),
            "verdict_change": deltas.get("verdict_delta"),
            "cracks_healed": deltas["healed"],
            "cracks_new": deltas["new"],
            "cracks_persisting": deltas["persisting"],
            "confidence_delta": deltas.get("confidence_delta"),
        },
        "calibration": {"status": "tracking", "note": _CAL_NOTE},
        "feedback": [],
    }
    if store is not None and ticker:
        review["vs_history"] = history_summary(store, ticker)

    if not deltas["had_prior"]:
        # cold store / first run for this entity — degrade gracefully, never raise.
        review["calibration"]["status"] = "insufficient_history"
        review["vs_prior_run"]["note"] = "insufficient history"
        review["feedback"] = ["Insufficient history — first stored run for this entity; "
                              "healed / persisting cracks will appear from the next run on."]
        return {"review": review}

    # Optional LLM narrative (live pipeline only). The deltas above are authoritative.
    if ask_claude is not None:
        base = pathlib.Path(prompts_dir)
        system = (base / "system.md").read_text(encoding="utf-8") + "\n\n" + (base / "reviewer.md").read_text(encoding="utf-8")
        user = (
            f"Current verdict {deltas['current_verdict']} (confidence {cur.get('confidence')}).\n"
            f"Code-computed deltas (authoritative — do not recompute): {json.dumps(deltas)}\n"
            "Write the `feedback` array (plain strings) only. No BUY/SELL/HOLD; "
            "set nothing about predictive calibration."
        )
        try:
            out = json.loads(ask_claude(system, user))
            fb = out.get("feedback") if isinstance(out, dict) else out
            if isinstance(fb, list):
                review["feedback"] = [str(x) for x in fb]
        except Exception:
            pass  # narrative is best-effort; the deterministic block already stands

    return {"review": review}


if __name__ == "__main__":  # offline smoke of the deterministic core
    cur = {"entity": {"ticker": "MSFT"}, "thesis_robustness": "Contested", "confidence": 0.62,
           "conflict_map": [{"claim_under_test": "Premium valuation is justified", "crack_type": "contradicted"}],
           "run": {"id": "r2"}}
    prior = {"thesis_robustness": "Breaks", "confidence": 0.55,
             "conflict_map": [{"claim_under_test": "Premium valuation is justified", "crack_type": "contradicted"},
                              {"claim_under_test": "Cloud margins keep expanding", "crack_type": "vulnerable"}],
             "run": {"id": "r1"}}
    print(json.dumps(run_review(cur, prior)["review"], indent=2))
