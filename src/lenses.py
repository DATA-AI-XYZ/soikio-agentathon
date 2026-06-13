"""lenses.py — the six analytical lenses + per-claim retrieval-query builder (EPIC-02 FEAT-02.1)."""
from __future__ import annotations

LENSES = ["macro", "fundamental", "technical", "risk", "valuation", "supply_chain"]
MVP_LENSES = ["fundamental", "risk", "valuation"]  # contest cut, per docs/scoring.md L46 + PRD R3 (ADR-0016)


def queries_for(claim: dict, entity_name: str) -> list[tuple[str, str]]:
    """(lens, retrieval-question) pairs for a claim across its tagged lenses."""
    base = claim.get("claim", "")
    out = []
    for lens in (claim.get("lenses") or MVP_LENSES):
        if lens not in LENSES:
            lens = "fundamental"
        out.append((lens, f"{entity_name}: {base} — {lens.replace('_', ' ')} evidence, risks, figures and contrary facts"))
    return out
