"""TESTPLAN-03.2.01 — coverage gate (citations.coverage_gate), reliability-spec §2.

The E7 boundary: no coverage → `data_gap` (off-map, lowers data_completeness); coverage + no
evidence → legitimate `unsupported` crack. Coverage is injected as a stub so the test is
deterministic and offline. Test names embed the -k selectors."""
import cio
import citations


def test_e7_data_gap():
    """AC-1 (E7) · an uncovered claim becomes a `data_gap` (no `unsupported` emitted), and a gap
    lowers data_completeness."""
    cracks = [{"claim_id": "c1", "crack_type": "unsupported", "point": "an obscure unsupported claim",
               "lens": "esg", "citations": []}]
    out, gaps = citations.coverage_gate(cracks, coverage_fn=lambda claim, lens: False)
    assert gaps == 1
    assert out[0]["crack_type"] == "data_gap"
    assert all(c["crack_type"] != "unsupported" for c in out)
    # the gap removes a usable lens → data_completeness drops (3 active lenses, one now a gap)
    assert cio.data_completeness(3 - gaps, 3) < cio.data_completeness(3, 3)


def test_legit_unsupported():
    """AC-2 · a covered claim with no supporting evidence stays a legitimate `unsupported` crack."""
    cracks = [{"claim_id": "c1", "crack_type": "unsupported", "point": "a covered but unsupported claim",
               "lens": "risk", "citations": []}]
    out, gaps = citations.coverage_gate(cracks, coverage_fn=lambda claim, lens: True)
    assert gaps == 0
    assert out[0]["crack_type"] == "unsupported"


def test_data_gap_off_map():
    """AC-3 · a `data_gap` never appears on the conflict map, while a real crack still does."""
    cracks = [
        {"claim_id": "c1", "crack_type": "unsupported", "point": "uncovered claim",
         "lens": "esg", "citations": [], "stance": "bear"},
        {"claim_id": "c2", "crack_type": "contradicted", "point": "a real, cited crack",
         "lens": "risk", "citations": ["S1"], "stance": "bear"},
    ]
    # only the esg lens is uncovered
    gated, gaps = citations.coverage_gate(cracks, coverage_fn=lambda claim, lens: lens != "esg")
    claims = [{"id": "c1", "load_bearing": False}, {"id": "c2", "load_bearing": True}]
    cmap = cio.build_conflict_map(claims, gated)
    types = {e["crack_type"] for e in cmap}
    assert "data_gap" not in types                       # off-map
    assert any(e["claim_id"] == "c2" for e in cmap)      # the real crack still maps
