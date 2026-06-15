"""TESTPLAN-02.3.02 — deterministic scorer (severity / robustness / confidence / determinism).

The scorer lives in src/cio.py (docs/scoring.md §intro mandates "a deterministic function in
src/cio.py"); the story's files_touched named scoring.py but the spec puts it in cio.py. Pure-logic,
fully offline — the load-bearing E8 determinism precondition. Test names embed the -k selectors."""
import cio

_CLAIMS = [{"id": "c1", "load_bearing": True}, {"id": "c2", "load_bearing": False}]


def test_severity_function():
    """AC-1 · severity table + single-source cap + uncited-vulnerable rejection."""
    assert cio._severity("contradicted", True, 2) == "high"
    assert cio._severity("contradicted", True, 1) == "medium"     # single-source cap
    assert cio._severity("contradicted", False, 3) == "medium"
    assert cio._severity("unsupported", True, 0) == "medium"
    assert cio._severity("vulnerable", False, 1) == "low"
    # uncited vulnerable is rejected at map-build (speculation, not a crack)
    cmap = cio.build_conflict_map(
        _CLAIMS, [{"claim_id": "c1", "crack_type": "vulnerable", "point": "x", "citations": [], "stance": "bear"}])
    assert cmap == []


def test_robustness_derivation():
    """AC-2 · Breaks > Contested > Holds, derived in order, ties favour conservative."""
    assert cio.robustness(_CLAIMS, [{"claim_id": "c1", "crack_type": "contradicted", "severity": "high"}]) == "Breaks"
    assert cio.robustness(_CLAIMS, [{"claim_id": "c1", "crack_type": "unsupported", "severity": "medium"}]) == "Breaks"
    assert cio.robustness(_CLAIMS, [{"claim_id": "c1", "crack_type": "vulnerable", "severity": "medium"}]) == "Contested"
    two_med = [{"claim_id": "c2", "crack_type": "a", "severity": "medium"},
               {"claim_id": "c2", "crack_type": "b", "severity": "medium"}]
    assert cio.robustness(_CLAIMS, two_med) == "Contested"
    assert cio.robustness(_CLAIMS, [{"claim_id": "c2", "crack_type": "vulnerable", "severity": "low"}]) == "Holds"
    assert cio.robustness(_CLAIMS, []) == "Holds"


def test_confidence_caps():
    """AC-3 · data_completeness<0.5 → ≤0.5; unresolved high → ≤0.45; zero-evidence load-bearing → ≤0.4."""
    assert cio.confidence([], 1.0) == 0.7
    assert cio.confidence([], 0.4) == 0.5
    assert cio.confidence([{"severity": "high"}], 1.0) == 0.45
    assert cio.confidence([], 1.0, zero_evidence_load_bearing=True) == 0.4
    assert cio.confidence([{"severity": "high"}], 0.4, zero_evidence_load_bearing=True) == 0.4  # most conservative
    # Breaks cap: a broken thesis (even a medium-severity unsupported Breaks) never reads high-confidence.
    assert cio.confidence([], 1.0, robustness="Breaks") == 0.5
    assert cio.confidence([{"severity": "medium"}], 1.0, robustness="Breaks") == 0.5
    assert cio.confidence([], 1.0, robustness="Holds") == 0.7                                   # non-Breaks unaffected
    # evidence-gap Breaks (unsupported load-bearing, no citations) lands at ≤ 0.4
    assert cio.confidence([{"severity": "medium"}], 1.0, robustness="Breaks",
                          zero_evidence_load_bearing=True) == 0.4


def test_determinism():
    """AC-4 · scoring the same crack set 100× yields identical severity/robustness/confidence."""
    cracks = [{"claim_id": "c1", "crack_type": "contradicted", "point": "x", "citations": ["S1", "S2"], "stance": "bear"}]
    results = set()
    for _ in range(100):
        cmap = cio.build_conflict_map(_CLAIMS, cracks)
        results.add((tuple(c["severity"] for c in cmap), cio.robustness(_CLAIMS, cmap), cio.confidence(cmap, 1.0)))
    assert len(results) == 1


def test_data_completeness_active_denominator():
    """AC-5 · denominator is the active lens count (3 for MVP, 6 for full), not a hardcoded 6."""
    assert cio.data_completeness(3, 3) == 1.0     # 3-lens MVP, all usable
    assert cio.data_completeness(3, 6) == 0.5     # 6-lens run divides by 6
    assert cio.data_completeness(0, 3) == 0.0
