"""TESTPLAN-02.1.01 — extract.py atomic claims.

Uses a recorded Claude response (llm.json_chat monkeypatched) per the testplan's "recorded response
or low-temperature call" — deterministic, offline, no token spend. Assertions are on structure, not
exact wording. Test names embed the -k selectors (atomic_claims, thin_input_no_fabrication,
entity_parse, schema_validates)."""
import extract
from extract import Extraction

_NORMAL = {
    "entity": {"ticker": "NVDA", "name": "NVIDIA"},
    "claims": [
        {"id": "c1", "claim": "Data center revenue keeps compounding", "load_bearing": True, "lenses": ["fundamental"], "horizon": "medium"},
        {"id": "c2", "claim": "Premium valuation is justified by growth", "load_bearing": True, "lenses": ["valuation"]},
        {"id": "c3", "claim": "Export controls are a manageable risk", "load_bearing": False, "lenses": ["risk"]},
        {"id": "c4", "claim": "Supply-chain position is a moat", "load_bearing": False, "lenses": ["supply_chain"]},
    ],
}


def _patch(monkeypatch, payload):
    monkeypatch.setattr(extract.llm, "json_chat", lambda *a, **k: payload)


def test_atomic_claims(monkeypatch):
    """AC-1 · a normal thesis yields 3–6 claims, each with id/claim/load_bearing/lenses."""
    _patch(monkeypatch, _NORMAL)
    out = extract.extract("NVDA is a durable buy-and-hold; data-center moat justifies the premium.")
    assert 3 <= len(out["claims"]) <= 6
    for c in out["claims"]:
        assert {"id", "claim", "load_bearing", "lenses"} <= set(c)
        assert isinstance(c["lenses"], list) and c["lenses"]


def test_thin_input_no_fabrication(monkeypatch):
    """AC-2 · a thin one-liner yields >=1 load-bearing claim and no invented claims."""
    thin = {"entity": {"ticker": "NVDA", "name": "NVIDIA"},
            "claims": [{"id": "c1", "claim": "NVIDIA keeps winning", "load_bearing": True}]}
    _patch(monkeypatch, thin)
    out = extract.extract("NVDA good")
    assert len(out["claims"]) == 1                       # exactly what the model emitted — nothing added
    assert any(c["load_bearing"] for c in out["claims"])
    assert out["claims"][0]["lenses"] == ["fundamental"]  # default applied, not fabricated content


def test_entity_parse(monkeypatch):
    """AC-3 · the entity (ticker + name) is parsed from the input."""
    _patch(monkeypatch, _NORMAL)
    out = extract.extract("NVDA thesis")
    assert out["entity"]["ticker"] == "NVDA"
    assert out["entity"]["name"] == "NVIDIA"


def test_schema_validates(monkeypatch):
    """AC-4 · output validates against the claim schema with no error."""
    _patch(monkeypatch, _NORMAL)
    out = extract.extract("NVDA thesis")
    Extraction.model_validate(out)
