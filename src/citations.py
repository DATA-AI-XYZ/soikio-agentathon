"""citations.py — the reliability guard (EPIC-03).

Two gates:
- cite-or-silence: a material point with no faithful citation is dropped, never shown.
- compliance: BUY / SELL / HOLD intent is blocked (without false-positiving buyback / sell-side / holds).
"""
from __future__ import annotations
import re

# Block the BUY/SELL/HOLD *instruction*, not every occurrence of the words (R7, reliability-spec §3).
# Match advisory INTENT, never substrings: allow "claims hold", "holds", "sell-side consensus",
# "buyback", "holding period", "buyers returned", "the bull case" — they describe, not instruct.
_CAPS = re.compile(r"\b(BUY|SELL|HOLD)\b")  # case-sensitive: the rating convention (a rating IS advice)
_INTENT = re.compile(
    r"\b(?:recommend(?:ed|ation)?|rate[ds]?|rating(?:\s+of)?|issue[ds]?\s+a|should)\s+"
    r"(?:(?:a|an|strong|the)\s+)*(buy|sell|hold)\b", re.I)
# Imperative transact actions on the security (reliability-spec §3): the verb + a position/security object.
_ACTION = re.compile(
    r"\b(?:buy|sell|accumulate|short|long)\s+"
    r"(?:the\s+|its\s+|this\s+|your\s+|more\s+)?(?:stock|shares|equity|position|name|security)\b", re.I)
# Bare imperative transact phrases that are advice on their own (no object needed).
_IMPERATIVE = re.compile(
    r"\b(?:take\s+profits?|trim\s+(?:the\s+|your\s+)?(?:position|stake|holding)|"
    r"go\s+(?:long|short)|add\s+to\s+(?:the\s+|your\s+)?position|exit\s+(?:the\s+|your\s+)?(?:position|stock|name)|"
    r"(?:buy|sell|accumulate)\s+(?:now|here|today))\b", re.I)
# A price target framed as an instruction ("target $200, buy" / "buy with a $200 target").
_TARGET = re.compile(
    r"(?:\b(?:buy|sell)\b[^.]{0,40}\bprice\s+target\b)|(?:\bprice\s+target\b[^.]{0,40}\b(?:buy|sell)\b)", re.I)


def block_advice(text: str) -> bool:
    """True only if the text gives a transact *instruction* (rating / recommendation / imperative action /
    instruction-framed price target). Matches advisory intent, not substrings (reliability-spec §3)."""
    t = text or ""
    return bool(_CAPS.search(t) or _INTENT.search(t) or _ACTION.search(t)
                or _IMPERATIVE.search(t) or _TARGET.search(t))


def faithful(points: list[dict], source_ids: set[str]) -> list[dict]:
    """Drop citations that don't map to a real source; drop material points left uncited (cite-or-silence)."""
    out = []
    for p in points:
        p["citations"] = [c for c in (p.get("citations") or []) if c in source_ids]
        ct = p.get("crack_type")
        if ct in ("contradicted", "vulnerable", "support") and not p["citations"]:
            continue  # material claim with no faithful source → silence it
        out.append(p)
    return out
