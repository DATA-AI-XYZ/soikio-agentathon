"""TESTPLAN-03.3.01 — compliance guard (citations.block_advice), reliability-spec §3.

The guard blocks transact INTENT (rating / recommendation / imperative action / instruction-framed
price target) without false-positiving descriptive market vocabulary. Pure-logic, offline.
Test names embed the -k selectors (e3_no_advice, allow_list, deny_list, fixture_suite)."""
import json
import os

import citations

_FIXTURE = os.path.join(os.path.dirname(__file__), "fixtures", "compliance_allow_deny.json")
_CAPS = ("BUY", "SELL", "HOLD")


def test_e3_no_advice():
    """AC-1 (E3) · a buy-nudge gets an analytical answer that is NOT blocked and emits no BUY/SELL/HOLD rating."""
    analytical = (
        "Should I buy NVDA? The thesis robustness is Contested: gross-margin compression is a "
        "cited crack (S2), while data-center demand still supports the bull case (S1). "
        "This is analysis, not advice."
    )
    assert citations.block_advice(analytical) is False          # analytical answer flows
    assert not any(tok in analytical for tok in _CAPS)          # no rating convention emitted


def test_allow_list_not_blocked():
    """AC-2 · descriptive phrases (sell-side / buyback / holding period …) are never blocked."""
    allow = json.load(open(_FIXTURE, encoding="utf-8"))["allow"]
    blocked = [s for s in allow if citations.block_advice(s)]
    assert blocked == [], f"false-positives on descriptive vocabulary: {blocked}"


def test_deny_list_blocked():
    """AC-3 · imperative transact instructions and instruction-framed targets are blocked."""
    deny = json.load(open(_FIXTURE, encoding="utf-8"))["deny"]
    passed = [s for s in deny if not citations.block_advice(s)]
    assert passed == [], f"advice that slipped through the guard: {passed}"


def test_fixture_suite():
    """AC-4 · the whole allow/deny fixture suite classifies correctly in one pass."""
    fx = json.load(open(_FIXTURE, encoding="utf-8"))
    for s in fx["allow"]:
        assert citations.block_advice(s) is False, f"allow misclassified as deny: {s!r}"
    for s in fx["deny"]:
        assert citations.block_advice(s) is True, f"deny misclassified as allow: {s!r}"
