"""agent.py — orchestration entry (EPIC-02 FEAT-02.4). thesis → cited Kintsugi brief."""
from __future__ import annotations
import time
import extract, agents, cio, citations, lenses


def run(thesis: str) -> dict:
    t0 = time.time()
    tel = {}

    t = time.time()
    extracted = extract.extract(thesis)
    tel["extract_s"] = round(time.time() - t, 1)

    t = time.time()
    sources = agents.gather_grounding(extracted)
    tel["retrieve_s"] = round(time.time() - t, 1)
    sids = {s["id"] for s in sources}

    t = time.time()
    bull = citations.faithful(agents.run_stance("bull", thesis, extracted, sources), sids)
    bear = citations.faithful(agents.run_stance("bear", thesis, extracted, sources), sids)
    caution = citations.faithful(
        agents.run_stance("caution", thesis, extracted, sources,
                          extra="The Bull and Bear have already run; surface what they missed."), sids)
    tel["agents_s"] = round(time.time() - t, 1)

    cracks = [p for p in (bear + caution) if p.get("crack_type") in ("contradicted", "unsupported", "vulnerable")]
    support = [p for p in bull if p.get("crack_type") == "support"]

    cmap = cio.build_conflict_map(extracted["claims"], cracks)
    active = len({l for c in extracted["claims"] for l in (c.get("lenses") or lenses.MVP_LENSES)}) or 3
    dc = round(len({s["lens"] for s in sources}) / max(active, 1), 2)
    verdict = cio.robustness(extracted["claims"], cmap)
    conf = cio.confidence(cmap, dc)

    t = time.time()
    brief_text, lean = cio.narrate(thesis, extracted, cmap, support, verdict, conf)
    tel["cio_s"] = round(time.time() - t, 1)

    compliance_ok = not citations.block_advice(brief_text)
    tel["total_s"] = round(time.time() - t0, 1)

    return {
        "entity": extracted.get("entity"), "thesis": thesis, "claims": extracted["claims"],
        "conflict_map": cmap, "support": support,
        "thesis_robustness": verdict, "equity_lean": lean,
        "confidence": conf, "data_completeness": dc,
        "brief": brief_text, "sources": sources,
        "compliance_ok": compliance_ok, "telemetry": tel,
    }
