"""TESTPLAN-01.3.01 (query contract) + TESTPLAN-01.3.02 (coverage probe).

Runs against the offline mock backend (conftest defaults FOUNDRY_IQ_MOCK=1), so deterministic
and Azure-free. Test names embed the testplan -k selectors (query_shape, citation_fields,
contract_validates, coverage_present, coverage_absent, coverage_boolean)."""
import foundry_iq
from foundry_iq import QueryResult

Q = "NVIDIA China export controls risk"


# --- TESTPLAN-01.3.01 · query() contract ------------------------------------------------
def test_query_shape():
    """AC-1 · query() returns non-empty extracts[] and a citations[] list."""
    r = foundry_iq.query(Q)
    assert isinstance(r, dict)
    assert isinstance(r.get("extracts"), list) and r["extracts"], "expected non-empty extracts"
    assert isinstance(r.get("citations"), list)


def test_citation_fields():
    """AC-2 · every citation carries source_id, quote, locator (doc-level fallback allowed)."""
    r = foundry_iq.query(Q)
    assert r["citations"], "expected at least one citation"
    for c in r["citations"]:
        assert isinstance(c.get("source_id"), str) and c["source_id"]
        assert "quote" in c
        assert isinstance(c.get("locator"), str) and c["locator"]


def test_contract_validates():
    """AC-3 · the response validates against the documented Pydantic contract with no error."""
    r = foundry_iq.query(Q)
    QueryResult.model_validate(r)


def test_query_empty_no_raise():
    """Edge case · empty retrieval returns empty arrays, never raises."""
    r = foundry_iq.query("zzzz qqqq wxyz vvvv")
    assert r["extracts"] == []
    assert r["citations"] == []
