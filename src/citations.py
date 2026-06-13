"""citations.py — the reliability guard (EPIC-03).

Two gates:
- cite-or-silence: a material point with no faithful citation is dropped, never shown.
- compliance: BUY / SELL / HOLD intent is blocked (without false-positiving buyback / sell-side / holds).
"""
from __future__ import annotations
import re

# Block the BUY/SELL/HOLD *instruction*, not every occurrence of the words (R7).
# Allowed: "claims hold", "holds", "sell-side", "buyback", "holding period".
_CAPS = re.compile(r"\b(BUY|SELL|HOLD)\b")  # case-sensitive: the rating convention
_INTENT = re.compile(
    r"\b(?:recommend(?:ed|ation)?|rate[ds]?|rating(?:\s+of)?|issue[ds]?\s+a|should)\s+"
    r"(?:a\s+|strong\s+)?(buy|sell|hold)\b", re.I)
_ACTION = re.compile(r"\b(buy|sell)\s+(?:the\s+|its\s+|this\s+)?(?:stock|shares|equity|position|name|security)\b", re.I)


def block_advice(text: str) -> bool:
    """True only if the text gives a BUY/SELL/HOLD *instruction* (rating / recommendation / action)."""
    t = text or ""
    return bool(_CAPS.search(t) or _INTENT.search(t) or _ACTION.search(t))


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
