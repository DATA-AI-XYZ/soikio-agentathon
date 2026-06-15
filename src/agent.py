"""agent.py — orchestration entry (EPIC-02 FEAT-02.4). thesis → cited Kintsugi brief.

One command runs extract → Bull/Bear/Caution → CIO → deterministic scorer and returns the scored
brief plus an inspectable `run` telemetry block. A single stance failure is isolated and recorded
as degraded (never silently dropped) so one slow/broken agent can't stall or void the whole run.
"""
from __future__ import annotations
import time, uuid, datetime, copy, re, json
import extract, agents, cio, citations, lenses, llm, memory, foundry_iq, domains

# Corporate suffixes / stopwords dropped when deriving distinctive entity match-terms from a name.
_NAME_STOP = {"corporation", "corp", "inc", "incorporated", "company", "co", "ltd", "limited",
              "plc", "the", "group", "holdings", "sa", "ag", "nv", "lp", "llc"}


def _entity_terms(entity: dict | None) -> list[str]:
    """Lower-cased terms that identify the resolved entity in source text: ticker + distinctive
    name tokens (suffixes/stopwords stripped). Used to tell on-entity retrieval from off-entity."""
    entity = entity or {}
    terms = [entity.get("ticker") or ""]
    terms += [w for w in re.findall(r"[A-Za-z]{2,}", entity.get("name") or "")
              if w.lower() not in _NAME_STOP]
    return [t.lower() for t in terms if t]


def _on_entity(sources: list[dict], terms: list[str]) -> list[dict]:
    """Sources whose content actually mentions the entity (case-insensitive). With no terms we
    can't discriminate, so every source counts (never falsely flag an entity as off-corpus)."""
    if not terms:
        return list(sources)
    return [s for s in sources if any(t in (s.get("content") or "").lower() for t in terms)]


def _zero_evidence_load_bearing(claims: list[dict], cmap: list[dict]) -> bool:
    """True if some load-bearing claim's ONLY cracks are `unsupported` with no citations — i.e. the
    thesis rests on a claim with no evidence either way (docs/scoring.md §3 → confidence ≤ 0.4)."""
    by_claim: dict[str, list[dict]] = {}
    for c in cmap:
        by_claim.setdefault(c.get("claim_id"), []).append(c)
    for claim in claims:
        if not claim.get("load_bearing"):
            continue
        entries = by_claim.get(claim["id"])
        if entries and all(e.get("crack_type") == "unsupported" and not e.get("citations") for e in entries):
            return True
    return False


def _corpus_version() -> str:
    """Stamp the brief with the current corpus generation (ADR-0022 / STORY-07.1.01) so recalled
    evidence can never be presented as fresh after a re-index. Best-effort: a signal failure must
    never break /analyze."""
    try:
        return foundry_iq.current_corpus_version()
    except Exception:
        return ""


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

    # --- off-corpus guard (correctness + cost) -----------------------------------------------
    # The KB only covers a handful of entities; any other ticker still retrieves off-entity chunks
    # that would score data_completeness 1.0 and a confident-looking "Breaks". If NOTHING retrieved
    # actually mentions the resolved entity, short-circuit BEFORE the expensive stance/domain/CIO
    # Claude calls and tell the user the entity isn't in the corpus.
    ent = extracted.get("entity") or {}
    terms = _entity_terms(ent)
    on_entity = _on_entity(sources, terms)
    if terms and not on_entity:
        name = ent.get("name") or ent.get("ticker") or "This entity"
        tel["total_s"] = round(time.time() - t0, 1)
        return {
            "entity": ent, "thesis": thesis, "entity_in_corpus": False,
            "message": f"{name} isn't in the knowledge base yet — add its filing to analyse it.",
            "thesis_robustness": None, "confidence": None, "data_completeness": 0.0,
            "sources": [], "run": {
                "id": uuid.uuid4().hex[:12],
                "timestamp": datetime.datetime.now(datetime.timezone.utc).isoformat(),
                "corpus_version": _corpus_version(), "retrievals": len(sources), "off_corpus": True,
            }, "telemetry": tel,
        }

    # --- domain specialists: six lenses in parallel, before the debate; failures are non-fatal --
    t = time.time()
    try:
        ask = lambda s, u: json.dumps(llm.json_chat(s, u))   # domains expect a JSON string back
        domain_findings = domains.run_all(extracted["claims"], foundry_iq, ask)
    except Exception as e:           # one slow/broken panel must never void the run
        domain_findings = []
        degraded.append({"agent": "domains", "error": type(e).__name__})
    tel["domains_s"] = round(time.time() - t, 1)

    t = time.time()
    bull = _safe_stance("bull", thesis, extracted, sources, sids, degraded)
    bear = _safe_stance("bear", thesis, extracted, sources, sids, degraded)
    caution = _safe_stance("caution", thesis, extracted, sources, sids, degraded,
                           extra="The Bull and Bear have already run; surface what they missed.")
    tel["agents_s"] = round(time.time() - t, 1)

    cracks = [p for p in (bear + caution) if p.get("crack_type") in ("contradicted", "unsupported", "vulnerable")]
    support = [p for p in bull if p.get("crack_type") == "support"]

    cmap = cio.build_conflict_map(extracted["claims"], cracks)
    cmap = cio.enrich_conflict_map(cmap, extracted["claims"], sources)  # claim_under_test + citation objects (output-schema)
    active_lenses = sorted({l for c in extracted["claims"] for l in (c.get("lenses") or lenses.MVP_LENSES)}) \
        or sorted(lenses.MVP_LENSES)
    lenses_with_evidence = sorted({s["lens"] for s in on_entity})   # on-entity coverage, not raw retrieval
    dc = round(len(lenses_with_evidence) / max(len(active_lenses), 1), 2)
    verdict = cio.robustness(extracted["claims"], cmap)
    zero_ev = _zero_evidence_load_bearing(extracted["claims"], cmap)
    conf = cio.confidence(cmap, dc, robustness=verdict, zero_evidence_load_bearing=zero_ev)

    t = time.time()
    brief_text, lean = cio.narrate(thesis, extracted, cmap, support, verdict, conf)
    tel["cio_s"] = round(time.time() - t, 1)

    compliance_ok = not citations.block_advice(brief_text)
    tel["total_s"] = round(time.time() - t0, 1)

    run_block = {
        "id": uuid.uuid4().hex[:12],
        "timestamp": datetime.datetime.now(datetime.timezone.utc).isoformat(),
        "model": getattr(llm, "MODEL", "claude"),
        "corpus_version": _corpus_version(),  # ADR-0022: freshness stamp — recall is fresh only if this matches current
        "total_s": tel["total_s"],
        "retrievals": len(sources),
        "lenses_with_evidence": lenses_with_evidence,
        "degraded": degraded,
    }

    brief = {
        "entity": extracted.get("entity"), "entity_in_corpus": True,
        "thesis": thesis, "claims": extracted["claims"],
        "conflict_map": cmap, "support": support, "domain_findings": domain_findings,
        "thesis_robustness": verdict, "equity_lean": lean,
        "confidence": conf, "data_completeness": dc,
        "active_lenses": active_lenses,
        "attack_bias": citations.attack_bias(cracks),
        "brief": brief_text, "sources": sources,
        "compliance_ok": compliance_ok,
        "run": run_block, "telemetry": tel,
    }

    # Persist every completed run (history / audit trail, STORY-08.2.01). Best-effort:
    # save a deep copy so the returned brief is never mutated, and a store failure
    # never breaks /analyze (run id = run_block["id"], so the response links to the store).
    try:
        memory.get_store().save_brief(copy.deepcopy(brief))
    except Exception:
        pass
    return brief
