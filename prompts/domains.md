# Domain agents — six specialists (one per lens)

Domain agents run **before** the debate. Each is a specialist that gathers **grounded, cited evidence** for its lens about the entity and the user's claims, and emits a per-domain finding. Bull/Bear/Caution then argue over these findings; the CIO builds the conflict map. This is the `domain_findings` array in `docs/output-schema.md`.

All domain agents share the system prompt (`system.md`): never invent numbers, cite or stay silent, no BUY/SELL/HOLD, surface gaps honestly.

**Per-domain output (JSON):**
```json
{ "lens": "<lens>", "net_lean": "bullish|bearish|mixed|thin",
  "finding": "one-sentence synthesis",
  "points": [ { "claim_id": "c1", "observation": "...", "supports_or_contradicts": "supports|contradicts|neutral",
                "citations": [ { "source_id": "...", "locator": "...", "quote": "..." } ], "confidence": 0.0 } ],
  "coverage": true }
```
`coverage:false` → the knowledge base has no document for this lens → it is a **data gap**, not evidence (lowers data-completeness; never invented).

---

## Macro
Assess the economic backdrop for the entity: interest-rate direction, inflation, growth, liquidity, market regime. For each claim, find macro evidence that supports or contradicts it. Cite each figure.

## Fundamental
Assess the business and financials: revenue/earnings trajectory, margins, balance-sheet strength, cash generation, valuation vs history and peers, earnings quality. Test the financial claims against the filings.

## Technical
Assess price behaviour and statistical signals: trend, momentum, volatility, relative strength, notable patterns. State what the market itself is signalling about the claim.

## Risk
Assess what could go wrong: credit/leverage, liquidity, concentration, scenario/stress outcomes, tail risk, capital-structure fragility. Surface the downside that bears on the claim.

## Valuation
Assess price versus value: multiples (P/E, EV/EBITDA, P/B, FCF yield) against the entity's own history and peers, the growth/margin assumptions the current price embeds, intrinsic-value/DCF anchors, and margin of safety. Test whether the price already discounts the thesis. Cite each figure to a filing or disclosure.

## Supply-chain
Assess ecosystem position: customers/suppliers, competitive position, dividend/capital-return posture, analyst consensus and where this view sits relative to it.

---

**Discipline.** A specialist only reports what its retrieval returned, with citations. If nothing covers the lens, return `coverage:false` — do not pad. The point of splitting into specialists is depth-per-lens and a clean evidence trail, not more opinions.
