"""TESTPLAN-02.2.01 — lenses.py query builder. Pure-logic, fully offline.

Test names embed the -k selectors (mvp_lenses, query_per_lens, expand_to_six)."""
import lenses


def test_mvp_lenses():
    """AC-1 · the 3 MVP lenses are exactly {fundamental, risk, valuation} (ADR-0016)."""
    assert set(lenses.MVP_LENSES) == {"fundamental", "risk", "valuation"}
    assert callable(lenses.queries_for)


def test_query_per_lens():
    """AC-2 · the builder returns exactly one query per active lens, each labelled + entity-scoped."""
    claim = {"claim": "Premium valuation is justified", "lenses": ["fundamental", "risk", "valuation"]}
    out = lenses.queries_for(claim, "NVIDIA")
    assert len(out) == 3
    assert [lens for lens, _ in out] == ["fundamental", "risk", "valuation"]
    for lens, q in out:
        assert "NVIDIA" in q
        assert lens.replace("_", " ") in q


def test_expand_to_six():
    """AC-3 · enabling all 6 lenses yields 6 queries with no caller change; full set has size 6."""
    assert len(lenses.LENSES) == 6
    claim = {"claim": "x", "lenses": list(lenses.LENSES)}
    out = lenses.queries_for(claim, "NVIDIA")
    assert len(out) == 6
    assert {lens for lens, _ in out} == set(lenses.LENSES)


def test_default_lenses_when_untagged():
    """A claim with no lenses falls back to the MVP set (one query each), nothing dropped."""
    out = lenses.queries_for({"claim": "x"}, "NVIDIA")
    assert [lens for lens, _ in out] == lenses.MVP_LENSES
