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


# --- TESTPLAN-02.2.03 · Bear -----------------------------------------------------------
_BEAR = {"points": [
    {"claim_id": "c1", "point": "Export controls contradict unrestricted China growth", "crack_type": "contradicted",
     "citations": ["S2"], "lens": "risk", "agent_severity_hint": "high", "confidence": 0.6},
    {"claim_id": "c1", "point": "No segment-margin disclosure supports the premium", "crack_type": "unsupported",
     "citations": [], "lens": "fundamental", "agent_severity_hint": "medium", "confidence": 0.4},
    {"claim_id": "c1", "point": "Premium valuation is vulnerable to a multiple de-rate", "crack_type": "vulnerable",
     "citations": ["S1"], "lens": "valuation", "agent_severity_hint": "medium", "confidence": 0.5},
]}


def test_bear_crack_types(monkeypatch):
    """AC-1 · every crack is typed contradicted/unsupported/vulnerable (+support allowed by schema)."""
    pts = _run(monkeypatch, "bear", _BEAR)
    allowed = {"contradicted", "unsupported", "vulnerable", "support"}
    assert pts and all(p["crack_type"] in allowed for p in pts)
    assert {p["crack_type"] for p in pts} >= {"contradicted", "unsupported", "vulnerable"}


def test_bear_citation_rules(monkeypatch):
    """AC-2 · contradicted/vulnerable carry ≥1 citation; unsupported carries none but names claim+lens."""
    pts = _run(monkeypatch, "bear", _BEAR)
    for p in pts:
        if p["crack_type"] in ("contradicted", "vulnerable"):
            assert p["citations"], f"{p['crack_type']} must be cited"
        if p["crack_type"] == "unsupported":
            assert not p["citations"]
            assert p["claim_id"] and p["lens"]


def test_bear_claim_ref(monkeypatch):
    """AC-3 · each crack references a claim_id and carries an agent_severity_hint."""
    pts = _run(monkeypatch, "bear", _BEAR)
    assert all(p["claim_id"] for p in pts)
    assert all(p.get("agent_severity_hint") for p in pts)


def test_bear_schema(monkeypatch):
    """AC-4 · output validates against the stance schema with stance == 'bear'."""
    pts = _run(monkeypatch, "bear", _BEAR)
    assert all(m.stance == "bear" for m in validate_stance(pts))


# --- TESTPLAN-02.2.04 · Caution --------------------------------------------------------
_CAUTION = {"points": [
    {"claim_id": "c1", "point": "Base rate: few hardware leaders hold share for a full decade", "crack_type": "vulnerable",
     "citations": ["S1"], "lens": "risk", "agent_severity_hint": "medium", "confidence": 0.4},
    {"claim_id": "c1", "point": "Data gap: no supply-chain concentration disclosure in the corpus", "crack_type": "unsupported",
     "citations": [], "lens": "supply_chain", "agent_severity_hint": "low", "confidence": 0.3},
]}


def test_caution_distinct(monkeypatch):
    """AC-1 · Caution output is distinct from Bear's cracks (no overlap of asserted points)."""
    bear = _run(monkeypatch, "bear", _BEAR)
    caution = _run(monkeypatch, "caution", _CAUTION)
    bear_points = {p["point"] for p in bear}
    caution_points = {p["point"] for p in caution}
    assert caution_points and not (caution_points & bear_points)


def test_caution_base_rates(monkeypatch):
    """AC-2 · surfaces ≥1 base-rate or data-gap concern when the corpus is thin."""
    pts = _run(monkeypatch, "caution", _CAUTION)
    text = " ".join(p["point"].lower() for p in pts)
    assert "base rate" in text or "data gap" in text


def test_caution_schema(monkeypatch):
    """AC-3 · output validates against the stance schema with stance == 'caution'."""
    pts = _run(monkeypatch, "caution", _CAUTION)
    assert all(m.stance == "caution" for m in validate_stance(pts))
