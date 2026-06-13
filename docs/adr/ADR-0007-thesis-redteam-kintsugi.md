# ADR-0007 — Pivot to thesis red-teaming; Kintsugi conflict map as headline

**Status:** Accepted · **Date:** 2026-06-12

## Context

An adversarial-critique of the original concept (a debate over a static public ticker) found two weaknesses: (1) it is **derivative** — bull/bear LLM debate adjudicated by a judge is the most trodden pattern in LLM-finance (e.g. TradingAgents), and (2) cite-or-silence grounding is now **table stakes** (AlphaSense, Hebbia, Bloomberg all ground-and-cite). The genuinely differentiated elements were the **adversarial conflict-surfacing** and the unrealised option to point the debate at the **user's own thesis**.

Separately, SoiKio's governing philosophy — the **Kintsugi Principle** (disagreement is signal; gild the cracks) — was not yet expressed in this entry, despite being the strongest framing for conflict-as-product.

## Decision

Two linked moves:

1. **Pivot the job from "analyse a ticker" to "red-team the user's investment thesis."** The user submits their thesis/memo; the public documents become the *grounding the thesis is tested against*, not the subject. Bull steelmans the thesis; Bear and Caution attack it; the CIO maps where it holds and where it breaks.
2. **Make the Kintsugi conflict map the headline output**, not a consensus verdict. The primary deliverable is a ranked map of cracks (contradicted / unsupported / vulnerable claims), each cited and each paired with what would resolve it. A thesis-robustness rating — **Holds / Contested / Breaks** — sits alongside it.

## Consequences

- **+** Clear, valuable user: the analyst / RIA / compliance reviewer who must show their work and wants their thesis stress-tested with an audit trail.
- **+** Genuine differentiation — confident-answer RAG tools don't red-team a position you already hold, and don't make the disagreement map the product.
- **+** Fixes the public-data-only ceiling without breaking clean-room: public docs are the grounding, the user's thesis is the target.
- **+** Authentic brand spine (Kintsugi) reinforcing the one element critics judged novel.
- **−** Adds a thesis-ingestion + claim-extraction step (the user's text in, claims out). Modest extra build.
- **−** Verdict family shifts from equity lean to thesis robustness; the equity lean (Bullish/Caution/Bearish) becomes secondary context, still no BUY/SELL.

## Related

Philosophy: `docs/kintsugi-principle.md`. Output shape: `docs/output-schema.md` (`thesis`, `conflict_map`, `thesis_robustness`). Conflict-as-signal lineage: ADR-0001. Compliance: ADR-0004.
