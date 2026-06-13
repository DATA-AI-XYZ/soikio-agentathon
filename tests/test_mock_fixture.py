"""TESTPLAN-01.3.03 — mock retrieval fixture behind the interface.

Deterministic + offline: a small fixture corpus (tests/fixtures/mock_corpus.json) with a staged
contradicted crack (a bull-support doc and a China/export-control risk doc that contradicts it),
injected over the mock backend. Asserts contract parity, env-only backend selection, and zero
Azure calls. Test names embed the -k selectors (contract_parity, backend_switch, offline_pipeline)."""
import json
import os

import foundry_iq

_FIX = os.path.join(os.path.dirname(__file__), "fixtures", "mock_corpus.json")


def _inject_fixture(monkeypatch):
    """Point the mock corpus at the deterministic fixture (no dependency on knowledge/*.htm)."""
    data = json.load(open(_FIX, encoding="utf-8"))
    monkeypatch.setattr(foundry_iq, "_mock_paras", [(d["source"], d["text"]) for d in data])


def test_contract_parity(monkeypatch):
    """AC-1 · mock query()/coverage() return the same Pydantic-validated shapes as the live client."""
    _inject_fixture(monkeypatch)
    r = foundry_iq.query("NVIDIA data center revenue growth")
    foundry_iq.QueryResult.model_validate(r)            # identical contract model to live
    assert r["extracts"] and r["citations"]
    for c in r["citations"]:
        assert set(c) >= {"source_id", "quote", "locator"}
    assert isinstance(foundry_iq.coverage("export controls China restrict"), bool)


def test_backend_switch(monkeypatch):
    """AC-2 · the mock is selected purely by env (FOUNDRY_IQ_BACKEND=mock) with no caller change."""
    monkeypatch.delenv("FOUNDRY_IQ_MOCK", raising=False)
    monkeypatch.setenv("FOUNDRY_IQ_BACKEND", "mock")
    _inject_fixture(monkeypatch)
    r = foundry_iq.query("AI training demand hyperscale")
    assert r["activity"] and r["activity"][0].get("mock") is True


def test_offline_pipeline(monkeypatch):
    """AC-3 · runs offline against the mock with zero Azure calls (the live client must never build)."""
    def _no_azure(*_a, **_k):
        raise AssertionError("live Azure client must not be constructed in mock mode")
    monkeypatch.setattr(foundry_iq, "_get_client", _no_azure)
    monkeypatch.setenv("FOUNDRY_IQ_BACKEND", "mock")
    _inject_fixture(monkeypatch)
    r = foundry_iq.query("NVIDIA China export controls restrict revenue")
    assert r["extracts"]                                # the staged crack is retrievable
    sources = {c["source_id"] for c in r["citations"]}
    assert any("risk" in s for s in sources)            # the contradiction doc surfaced
