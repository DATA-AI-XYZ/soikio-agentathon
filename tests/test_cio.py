"""TESTPLAN-02.3.01 — cio.py conflict map (dedup, ranking, resolutions, brief fields, stance weights).

Deterministic-structure assertions on fixture stance inputs; the one LLM touchpoint (narrate) is
mocked. Test names embed the -k selectors."""
import cio

_CLAIMS = [
    {"id": "c1", "claim": "Data center revenue compounds", "load_bearing": True},
    {"id": "c2", "claim": "Valuation is justified", "load_bearing": False},
]


def test_dedup_merged_from():
    """AC-1 · two cracks sharing (claim_id, crack_type) merge: citations unioned, merged_from kept."""
    cracks = [
        {"claim_id": "c1", "crack_type": "contradicted", "point": "Export controls hit China rev",
         "citations": ["S2"], "lens": "risk", "stance": "bear"},
        {"claim_id": "c1", "crack_type": "contradicted", "point": "China ban repeats the crack",
         "citations": ["S5"], "lens": "macro", "stance": "caution"},
    ]
    cmap = cio.build_conflict_map(_CLAIMS, cracks)
    assert len(cmap) == 1
    assert cmap[0]["citations"] == ["S2", "S5"]      # unioned + sorted
    assert cmap[0]["merged_from"]                    # provenance kept — no silent drop


def test_rank_order():
    """AC-2 · ranked by severity desc, then distinct-citation count desc, then claim_id."""
    cracks = [
        {"claim_id": "c2", "crack_type": "vulnerable", "point": "minor", "citations": ["S1"], "stance": "caution"},
        {"claim_id": "c1", "crack_type": "contradicted", "point": "big", "citations": ["S2", "S3"], "stance": "bear"},
    ]
    cmap = cio.build_conflict_map(_CLAIMS, cracks)
    order = {"high": 0, "medium": 1, "low": 2}
    sev = [c["severity"] for c in cmap]
    assert sev == sorted(sev, key=lambda s: order[s])
    assert cmap[0]["claim_id"] == "c1"               # high-severity load-bearing crack first


def test_resolution_concrete(monkeypatch):
    """AC-3 · a generic resolution from the LLM is rejected and regenerated to a concrete one."""
    cracks = [{"claim_id": "c1", "crack_type": "contradicted", "point": "x",
               "citations": ["S2", "S3"], "lens": "risk", "stance": "bear"}]
    cmap = cio.build_conflict_map(_CLAIMS, cracks)
    monkeypatch.setattr(cio.llm, "json_chat",
                        lambda *a, **k: {"brief": "b", "equity_lean": "Bearish", "resolutions": ["more disclosure"]})
    cio.narrate("thesis", {"claims": _CLAIMS}, cmap, [], "Breaks", 0.45)
    assert not cio._is_generic(cmap[0]["what_would_resolve_it"])
    assert cio._is_generic("more disclosure")
    assert not cio._is_generic("Q3 segment-margin disclosure showing cloud gross margin >= prior period")


def test_brief_fields():
    """AC-4 · the brief header has weighed_stances, thesis_robustness, equity_lean, confidence."""
    cmap = cio.build_conflict_map(_CLAIMS, [])
    points = [{"stance": "bull", "citations": ["S1"]}, {"stance": "bear", "citations": ["S2"]}]
    brief = cio.brief_fields(_CLAIMS, points, cmap, 1.0, equity_lean="Caution")
    assert {"weighed_stances", "thesis_robustness", "equity_lean", "confidence"} <= set(brief)


def test_stance_weights_evidence_proportional():
    """AC-5 · weights = (cited_points+0.05)/Σ, sum to 1.0, deterministic, 1/3 fallback (ADR-0009)."""
    points = [
        {"stance": "bull", "citations": ["S1"]}, {"stance": "bull", "citations": ["S2"]},
        {"stance": "bear", "citations": ["S3"]},
        {"stance": "caution", "citations": []},      # uncited → does not earn weight
    ]
    w = cio.stance_weights(points)
    assert abs(sum(w.values()) - 1.0) < 1e-9
    assert w["bull"] > w["bear"] > w["caution"]
    assert abs(w["bull"] - round(2.05 / 3.15, 4)) < 1e-4
    assert cio.stance_weights(points) == w           # deterministic
    eq = cio.stance_weights([])                       # all-zero → equal 1/3 fallback
    assert eq["bull"] == eq["bear"] == eq["caution"]
