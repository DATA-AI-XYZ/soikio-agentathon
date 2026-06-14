"""TESTPLAN-02.4.01 — agent.py end-to-end pipeline + run telemetry.

The LLM stances (Claude) and the CIO narration are monkeypatched to deterministic fakes, and
grounding is stubbed, so the pipeline is exercised offline with zero Azure/Anthropic calls. Test
names embed the -k selectors (end_to_end, telemetry, no_azure_calls, degraded_agent)."""
import agent
import agents
import cio
import extract
import foundry_iq

THESIS = "NVIDIA data-center revenue compounds; the valuation is justified by AI demand."

_EXTRACTED = {
    "entity": {"name": "NVIDIA", "ticker": "NVDA"},
    "claims": [{"id": "c1", "claim": "Data-center revenue compounds", "load_bearing": True,
                "lenses": ["risk", "valuation"]}],
}
_SOURCES = [{"id": "S1", "lens": "risk", "claim_id": "c1",
             "content": "China export controls may reduce NVIDIA data-center revenue."}]


def _fake_run_stance(name, thesis, extracted, sources, extra=""):
    cid = extracted["claims"][0]["id"]
    if name == "bull":
        return [{"claim_id": cid, "point": "AI demand supports the thesis", "crack_type": "support",
                 "citations": ["S1"], "lens": "risk", "stance": "bull"}]
    if name == "bear":
        return [{"claim_id": cid, "point": "Export controls contradict the revenue path", "crack_type": "contradicted",
                 "citations": ["S1"], "lens": "risk", "stance": "bear"}]
    return [{"claim_id": cid, "point": "Valuation leaves no margin for error", "crack_type": "vulnerable",
             "citations": ["S1"], "lens": "valuation", "stance": "caution"}]


def _fake_narrate(*_a, **_k):
    return ("The China crack (S1) contests the data-center thesis; valuation adds fragility.", "Caution")


def _stub_offline(monkeypatch):
    monkeypatch.setattr(extract, "extract", lambda thesis: _EXTRACTED)
    monkeypatch.setattr(agents, "gather_grounding", lambda extracted, **k: list(_SOURCES))
    monkeypatch.setattr(agents, "run_stance", _fake_run_stance)
    monkeypatch.setattr(cio, "narrate", _fake_narrate)


def test_end_to_end(monkeypatch):
    """AC-1 · a thesis runs end to end and returns a scored CIO brief (verdict + conflict map)."""
    _stub_offline(monkeypatch)
    brief = agent.run(THESIS)
    assert brief["thesis_robustness"] in ("Holds", "Contested", "Breaks")
    assert isinstance(brief["conflict_map"], list) and brief["conflict_map"]   # cracks survived
    assert brief["compliance_ok"] is True                                      # no advice in the brief


def test_telemetry(monkeypatch):
    """AC-2 · the `run` telemetry block carries id, timestamp, model, total time, retrievals, lenses."""
    _stub_offline(monkeypatch)
    run = agent.run(THESIS)["run"]
    for key in ("id", "timestamp", "model", "total_s", "retrievals", "lenses_with_evidence"):
        assert key in run, f"missing telemetry key: {key}"
    assert run["retrievals"] == len(_SOURCES)
    assert "risk" in run["lenses_with_evidence"]


def test_no_azure_calls(monkeypatch):
    """AC-3 · runs offline against the mock — the live Azure client must never be constructed."""
    def _no_azure(*_a, **_k):
        raise AssertionError("live Azure client must not be constructed in mock mode")
    monkeypatch.setattr(foundry_iq, "_get_client", _no_azure)
    monkeypatch.setattr(extract, "extract", lambda thesis: _EXTRACTED)
    monkeypatch.setattr(agents, "run_stance", _fake_run_stance)
    monkeypatch.setattr(cio, "narrate", _fake_narrate)
    monkeypatch.setenv("FOUNDRY_IQ_BACKEND", "mock")
    brief = agent.run(THESIS)            # gather_grounding runs against the mock; must not raise
    assert brief["thesis_robustness"] in ("Holds", "Contested", "Breaks")


def test_degraded_agent(monkeypatch):
    """AC-4 · one stance forced to fail is recorded as degraded, not silently dropped; the run completes."""
    _stub_offline(monkeypatch)

    def _bear_fails(name, thesis, extracted, sources, extra=""):
        if name == "bear":
            raise RuntimeError("bear timed out")
        return _fake_run_stance(name, thesis, extracted, sources, extra)

    monkeypatch.setattr(agents, "run_stance", _bear_fails)
    brief = agent.run(THESIS)
    degraded = {d["agent"] for d in brief["run"]["degraded"]}
    assert "bear" in degraded                                  # recorded, not dropped
    assert brief["thesis_robustness"] in ("Holds", "Contested", "Breaks")   # run still completes
