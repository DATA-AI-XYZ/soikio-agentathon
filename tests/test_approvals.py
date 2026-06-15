"""TESTPLAN — approvals.py: the server-side human-in-the-loop run gate.

Pure/offline: the in-memory store, the one-time run_token, the Telegram callback parser, and the
webhook->decision->finalize flow (with a fake notifier). No network, no Telegram, no Azure.
"""
import approvals
import pytest


@pytest.fixture(autouse=True)
def _clear_state():
    approvals._APPROVALS.clear()
    approvals._TOKENS.clear()
    approvals._notifier = None
    yield
    approvals._APPROVALS.clear()
    approvals._TOKENS.clear()
    approvals._notifier = None


def test_create_then_pending():
    aid = approvals.create_approval("Jane", "jane@firm.com", "NVDA durable moat")
    assert approvals.get_approval(aid) == {"status": "pending"}      # no run_token while pending


def test_approve_mints_one_time_token():
    aid = approvals.create_approval("Jane", "jane@firm.com", "thesis")
    assert approvals.decide(aid, "approved") is True
    view = approvals.get_approval(aid)
    assert view["status"] == "approved" and view.get("run_token")
    token = view["run_token"]
    assert approvals.consume_token(token) is True                   # first use ok
    assert approvals.consume_token(token) is False                  # one-time: second use rejected


def test_reject_no_token():
    aid = approvals.create_approval("Jane", "jane@firm.com", "thesis")
    assert approvals.decide(aid, "rejected") is True
    assert approvals.get_approval(aid) == {"status": "rejected"}     # no run_token on reject


def test_decide_idempotent():
    aid = approvals.create_approval("Jane", "jane@firm.com", "thesis")
    assert approvals.decide(aid, "approved") is True
    assert approvals.decide(aid, "rejected") is False               # already decided — ignored
    assert approvals.get_approval(aid)["status"] == "approved"


def test_consume_rejects_missing_and_bogus():
    assert approvals.consume_token(None) is False
    assert approvals.consume_token("") is False
    assert approvals.consume_token("deadbeef") is False


def test_consume_rejects_expired(monkeypatch):
    aid = approvals.create_approval("Jane", "jane@firm.com", "thesis")
    approvals.decide(aid, "approved")
    token = approvals.get_approval(aid)["run_token"]
    approvals._TOKENS[token]["_t"] -= (approvals._TTL_S + 1)         # age it past the TTL
    assert approvals.consume_token(token) is False


def test_telegram_parse_callback():
    n = approvals.TelegramNotifier("tok", "123")
    assert n.parse_callback({"callback_query": {"data": "approve:abc"}}) == ("approve", "abc")
    assert n.parse_callback({"callback_query": {"data": "reject:xyz"}}) == ("reject", "xyz")
    assert n.parse_callback({"message": {"text": "hi"}}) is None     # not a decision callback
    assert n.parse_callback({"callback_query": {"data": "noop:abc"}}) is None


class _FakeNotifier(approvals.Notifier):
    def __init__(self):
        self.sent = []
        self.finalized = []

    def send_request(self, approval):
        self.sent.append(approval)

    def parse_callback(self, payload):
        return approvals.TelegramNotifier.parse_callback(self, payload)

    def finalize(self, payload, decision):
        self.finalized.append(decision)


def test_handle_callback_approves_and_finalizes():
    fake = _FakeNotifier()
    approvals._notifier = fake
    aid = approvals.create_approval("Jane", "jane@firm.com", "thesis")
    approvals.handle_callback({"callback_query": {"id": "1", "data": f"approve:{aid}",
                                                  "message": {"chat": {"id": 5}, "message_id": 9}}})
    assert approvals.get_approval(aid)["status"] == "approved"
    assert approvals.get_approval(aid).get("run_token")
    assert fake.finalized == ["approved"]


def test_request_approval_sends(monkeypatch):
    fake = _FakeNotifier()
    approvals._notifier = fake
    aid = approvals.request_approval("Jane", "jane@firm.com", "my thesis")
    assert fake.sent and fake.sent[0]["id"] == aid and fake.sent[0]["thesis"] == "my thesis"
    assert approvals.get_approval(aid)["status"] == "pending"
