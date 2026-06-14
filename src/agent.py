"""agent.py — orchestration entry (EPIC-02 FEAT-02.4). thesis → cited Kintsugi brief.

One command runs extract → Bull/Bear/Caution → CIO → deterministic scorer and returns the scored
brief plus an inspectable `run` telemetry block. A single stance failure is isolated and recorded
as degraded (never silently dropped) so one slow/broken agent can't stall or void the whole run.
"""
from __future__ import annotations
import time, uuid, datetime
import extract, agents, cio, citations, lenses, llm


def _safe_stance(name, thesis, extracted, sources, sids, degraded, extra=""):
    """Run one stance under the citation gate; on failure record it degraded and return no points."""
    try:
        return citations.faithful(agents.run_stance(name, thesis, extracted, sources, extra=extra), sids)
    except Exception as e:  # isolate: one agent failing must not void the run (AC-4)
        degraded.append({"agent": name, "error": type(e).__name__})
        return []


def run(thesis: str) -> dict:
    t0 = time.time()
    tel: dict = {}
    degraded: list[dict] = []

    t = time.time()
    extracted = extract.extract(thesis)
    tel["extract_s"] = round(time.time() - t, 1)

    t = time.time()
    sources = agents.gather_grounding(extracted)
    tel["retrieve_s"] = round(time.time() - t, 1)
    sids = {s["id"] for s in sources}

    t = time.time()
    bull = _safe_stance("bull", thesis, extracted, sources, sids, degraded)
    bear = _safe_stance("bear", thesis, extracted, sources, sids, degraded)
    caution = _safe_stance("caution", thesis, extracted, sources, sids, degraded,
                           extra="The Bull and Bear have already run; surface what they missed.")
    tel["agents_s"] = round(time.time() - t, 1)

    cracks = [p for p in (bear + caution) if p.get("crack_type") in ("contradicted", "unsupported", "vulnerable")]
    support = [p for p in bull if p.get("crack_type") == "support"]

    cmap = cio.build_conflict_map(extracted["claims"], cracks)
    active_lenses = sorted({l for c in extracted["claims"] for l in (c.get("lenses") or lenses.MVP_LENSES)}) \
        or sorted(lenses.MVP_LENSES)
    lenses_with_evidence = sorted({s["lens"] for s in sources})
    dc = round(len(lenses_with_evidence) / max(len(active_lenses), 1), 2)
    verdict = cio.robustness(extracted["claims"], cmap)
    conf = cio.confidence(cmap, dc)

    t = time.time()
    brief_text, lean = cio.narrate(thesis, extracted, cmap, support, verdict, conf)
    tel["cio_s"] = round(time.time() - t, 1)

    compliance_ok = not citations.block_advice(brief_text)
    tel["total_s"] = round(time.time() - t0, 1)

    run_block = {
        "id": uuid.uuid4().hex[:12],
        "timestamp": datetime.datetime.now(datetime.timezone.utc).isoformat(),
        "model": getattr(llm, "MODEL", "claude"),
        "total_s": tel["total_s"],
        "retrievals": len(sources),
        "lenses_with_evidence": lenses_with_evidence,
        "degraded": degraded,
    }

    return {
        "entity": extracted.get("entity"), "thesis": thesis, "claims": extracted["claims"],
        "conflict_map": cmap, "support": support,
        "thesis_robustness": verdict, "equity_lean": lean,
        "confidence": conf, "data_completeness": dc,
        "active_lenses": active_lenses,
        "attack_bias": citations.attack_bias(cracks),
        "brief": brief_text, "sources": sources,
        "compliance_ok": compliance_ok,
        "run": run_block, "telemetry": tel,
    }
