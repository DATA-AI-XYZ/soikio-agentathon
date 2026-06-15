"""approvals.py — human-in-the-loop run gate (Telegram), enforced server-side.

The repo is public and `/analyze` is a public endpoint, so the gate CANNOT live in the UI:
a run is allowed only with a one-time `run_token` that is minted when an approver taps
**Approve** in Telegram. `server.py` calls this module; the UI only collects name/email and polls.

State is in-memory and the Container App is pinned to a single replica (min=max=1), so the
Telegram webhook, the browser poll and `/analyze` all share one process's memory — no DB needed
(approvals are ephemeral: seconds-to-minutes). A redeploy/restart drops in-flight approvals, which
is acceptable for this flow.

Notifier seam: the transport sits behind a tiny `Notifier` interface (`send_request` / `parse_callback`
/ `finalize`) so a Discord/WhatsApp backend can be dropped in without touching the approval flow.
"""
from __future__ import annotations
import json
import threading
import time
import urllib.request
import uuid

import config

# Secrets (keyless, ADR-0010): env var first for local dev, else Key Vault by secret name.
_BOT_TOKEN_ENV, _BOT_TOKEN_KV = "TELEGRAM_BOT_TOKEN", "telegram-bot-token"
_CHAT_ID_ENV, _CHAT_ID_KV = "TELEGRAM_CHAT_ID", "telegram-chat-id"
_WEBHOOK_SECRET_ENV, _WEBHOOK_SECRET_KV = "TELEGRAM_WEBHOOK_SECRET", "telegram-webhook-secret"

_TTL_S = 900   # an approval / run_token is valid ~15 min, then it's stale


# --- notifier seam -------------------------------------------------------------------------
class Notifier:
    """Approval transport. Swap Telegram for Discord/WhatsApp by implementing these three."""

    def send_request(self, approval: dict) -> None:
        """Push an approval request (with Approve/Reject affordances) to the approver."""
        raise NotImplementedError

    def parse_callback(self, payload: dict) -> tuple[str, str] | None:
        """Map an inbound webhook payload to (action, approval_id) where action ∈ approve|reject,
        or None if the payload isn't an actionable decision."""
        raise NotImplementedError

    def finalize(self, payload: dict, decision: str) -> None:
        """Acknowledge the decision back on the transport (e.g. edit the message)."""
        raise NotImplementedError


class _NullNotifier(Notifier):
    """Used when Telegram isn't configured: keeps the app importable/testable. The gate stays
    fail-closed — no notifier means no approvals, so no run_token is ever minted."""

    def send_request(self, approval: dict) -> None:
        raise RuntimeError("approval transport not configured (set TELEGRAM_BOT_TOKEN / TELEGRAM_CHAT_ID)")

    def parse_callback(self, payload: dict) -> tuple[str, str] | None:
        return None

    def finalize(self, payload: dict, decision: str) -> None:
        return None


class TelegramNotifier(Notifier):
    """Telegram Bot API transport. Plain-text messages (no parse_mode) so arbitrary thesis text
    can never break message formatting."""

    _API = "https://api.telegram.org/bot{token}/{method}"

    def __init__(self, token: str, chat_id: str):
        self._token = token
        self._chat_id = chat_id

    def _call(self, method: str, payload: dict) -> dict:
        url = self._API.format(token=self._token, method=method)
        data = json.dumps(payload).encode("utf-8")
        req = urllib.request.Request(url, data=data, headers={"Content-Type": "application/json"})
        with urllib.request.urlopen(req, timeout=10) as r:   # noqa: S310 (fixed api.telegram.org host)
            return json.loads(r.read().decode("utf-8"))

    def send_request(self, approval: dict) -> None:
        text = (
            "SoiKio — run approval requested\n\n"
            f"Requester: {approval['name']} ({approval['email']})\n\n"
            f"Thesis:\n{approval['thesis']}\n\n"
            "Approve this run of the four-agent red-team?"
        )
        keyboard = {"inline_keyboard": [[
            {"text": "✅ Approve", "callback_data": f"approve:{approval['id']}"},
            {"text": "❌ Reject", "callback_data": f"reject:{approval['id']}"},
        ]]}
        self._call("sendMessage", {"chat_id": self._chat_id, "text": text, "reply_markup": keyboard})

    def parse_callback(self, payload: dict) -> tuple[str, str] | None:
        cq = (payload or {}).get("callback_query") or {}
        data = cq.get("data") or ""
        action, _, approval_id = data.partition(":")
        if action in ("approve", "reject") and approval_id:
            return action, approval_id
        return None

    def finalize(self, payload: dict, decision: str) -> None:
        cq = (payload or {}).get("callback_query") or {}
        label = "Approved ✅" if decision == "approved" else "Rejected ❌"
        msg = cq.get("message") or {}
        chat_id = (msg.get("chat") or {}).get("id")
        message_id = msg.get("message_id")
        try:                                              # best-effort: pop the spinner on the tapped button
            if cq.get("id"):
                self._call("answerCallbackQuery", {"callback_query_id": cq["id"], "text": label})
        except Exception:
            pass
        try:                                              # best-effort: rewrite the message to the outcome
            if chat_id and message_id:
                self._call("editMessageText", {"chat_id": chat_id, "message_id": message_id,
                                                "text": f"SoiKio run — {label}"})
        except Exception:
            pass


_notifier: Notifier | None = None


def get_notifier() -> Notifier:
    """The configured notifier (cached). TelegramNotifier when token+chat are resolvable, else a
    fail-closed null notifier."""
    global _notifier
    if _notifier is None:
        token = config.get_secret(_BOT_TOKEN_ENV, _BOT_TOKEN_KV)
        chat_id = config.get_secret(_CHAT_ID_ENV, _CHAT_ID_KV)
        _notifier = TelegramNotifier(token, chat_id) if (token and chat_id) else _NullNotifier()
    return _notifier


def webhook_secret() -> str:
    """The expected value of the Telegram `X-Telegram-Bot-Api-Secret-Token` header."""
    return config.get_secret(_WEBHOOK_SECRET_ENV, _WEBHOOK_SECRET_KV)


# --- in-memory approval store (single replica; guarded for the threadpool) ------------------
_LOCK = threading.Lock()
_APPROVALS: dict[str, dict] = {}      # approval_id -> record
_TOKENS: dict[str, dict] = {}         # run_token   -> {approval_id, consumed, _t}


def _now_iso() -> str:
    import datetime
    return datetime.datetime.now(datetime.timezone.utc).isoformat()


def create_approval(name: str, email: str, thesis: str) -> str:
    """Store a pending approval and return its id."""
    approval_id = uuid.uuid4().hex
    with _LOCK:
        _APPROVALS[approval_id] = {
            "id": approval_id, "name": name, "email": email, "thesis": thesis,
            "status": "pending", "created_at": _now_iso(), "_t": time.time(),
        }
    return approval_id


def request_approval(name: str, email: str, thesis: str) -> str:
    """Create a pending approval and push the request to the approver. Raises if the transport
    can't deliver (so the API surfaces a clear failure rather than a silent forever-wait)."""
    approval_id = create_approval(name, email, thesis)
    with _LOCK:
        snapshot = dict(_APPROVALS[approval_id])
    get_notifier().send_request(snapshot)   # may raise (network / not configured) — let it propagate
    return approval_id


def get_approval(approval_id: str) -> dict | None:
    """Poll view: {status[, run_token]}. run_token is only exposed once approved."""
    with _LOCK:
        a = _APPROVALS.get(approval_id)
        if not a:
            return None
        out = {"status": a["status"]}
        if a["status"] == "approved" and a.get("run_token"):
            out["run_token"] = a["run_token"]
        return out


def decide(approval_id: str, decision: str) -> bool:
    """Apply approve/reject to a still-pending approval; mint a one-time run_token on approval.
    Returns True if the decision was applied (idempotent: a second decision is ignored)."""
    if decision not in ("approved", "rejected"):
        return False
    with _LOCK:
        a = _APPROVALS.get(approval_id)
        if not a or a["status"] != "pending":
            return False
        a["status"] = decision
        if decision == "approved":
            token = uuid.uuid4().hex
            a["run_token"] = token
            _TOKENS[token] = {"approval_id": approval_id, "consumed": False, "_t": time.time()}
        return True


def consume_token(run_token: str | None) -> bool:
    """The actual /analyze guard: True only if the token is approved, unconsumed and unexpired —
    and it is atomically marked consumed (one-time use) under the lock."""
    if not run_token:
        return False
    with _LOCK:
        rec = _TOKENS.get(run_token)
        if not rec or rec["consumed"] or (time.time() - rec["_t"] > _TTL_S):
            return False
        rec["consumed"] = True
        return True


def handle_callback(payload: dict) -> None:
    """Webhook entry: parse the decision, apply it, and acknowledge on the transport."""
    notifier = get_notifier()
    parsed = notifier.parse_callback(payload)
    if not parsed:
        return
    action, approval_id = parsed
    decision = "approved" if action == "approve" else "rejected"
    if decide(approval_id, decision):
        notifier.finalize(payload, decision)
