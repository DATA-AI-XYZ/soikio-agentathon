"""TESTPLAN-02.2.02/03/04 — the three stance agents (Bull / Bear / Caution).

The stances are consolidated in src/agents.py behind run_stance() (ADR-0017). Claude is mocked with
recorded stance responses (the testplans' allowed "recorded fixture") so the tests are deterministic
and offline — they verify run_stance's plumbing (prompt load, stance tagging, return shape) and the
StancePoint contract, not the model's reasoning. Test names embed the -k selectors."""
import agents
from agents import validate_stance

_THESIS = "NVDA is a durable buy-and-hold; the data-center moat justifies the premium."
_EXTRACTED = {
    "entity": {"ticker": "NVDA", "name": "NVIDIA"},
    "claims": [{"id": "c1", "claim": "Data center revenue compounds", "load_bearing": True, "lenses": ["fundamental"]}],
}
_SOURCES = [
    {"id": "S1", "lens": "fundamental", "claim_id": "c1", "content": "Data center revenue grew sharply."},
    {"id": "S2", "lens": "risk", "claim_id": "c1", "content": "Export controls restrict advanced GPU sales to China."},
]

_BULL = {"points": [
    {"claim_id": "c1", "point": "Data-center demand strongly supports the growth thesis", "crack_type": "support",
     "citations": ["S1"], "lens": "fundamental", "agent_severity_hint": "low", "confidence": 0.7},
]}


def _run(monkeypatch, name, payload):
    monkeypatch.setattr(agents.llm, "json_chat", lambda *a, **k: payload)
    return agents.run_stance(name, _THESIS, _EXTRACTED, _SOURCES)


# --- TESTPLAN-02.2.02 · Bull -----------------------------------------------------------
def test_bull_points_cited(monkeypatch):
    """AC-1 · lens-tagged supporting points, each with a non-empty citations list."""
    pts = _run(monkeypatch, "bull", _BULL)
    assert pts and all(p["citations"] for p in pts)
    assert all(p["lens"] for p in pts)
    assert all(p["stance"] == "bull" for p in pts)


def test_bull_point_fields(monkeypatch):
    """AC-2 · every point has lens, the asserted claim (`point`), citations, confidence."""
    pts = _run(monkeypatch, "bull", _BULL)
    for p in pts:
        assert {"lens", "point", "citations", "confidence"} <= set(p)


def test_bull_schema(monkeypatch):
    """AC-3 · output validates against the stance schema with stance == 'bull'."""
    pts = _run(monkeypatch, "bull", _BULL)
    models = validate_stance(pts)
    assert models and all(m.stance == "bull" for m in models)
