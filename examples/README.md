# Examples — sample thesis & the staged contradicted crack

`thesis.txt` is the demo input: a **bull thesis on NVIDIA (NVDA)**. It is authored *after* the
corpus so the red-team is guaranteed to find at least one genuine, citable crack on demo day
(FEAT-01.2 staged crack).

## Thesis ↔ contradiction pairing

| Load-bearing claim in `thesis.txt` | Contradicting document | How it cuts against the claim |
|---|---|---|
| **Claim 3 — "global reach, including continued access to the large China market, supports sustained double-digit data-center revenue growth"** | `knowledge/NVDA-10-K-2026-02-25.htm` (NVIDIA FY2026 10-K, Risk Factors) | The 10-K's own risk-factor language on **U.S. export controls / restrictions on selling its products into China** directly contradicts the thesis's assumption of *continued* China-market access — i.e. the company's filed disclosure says the very access the bull case leans on is at risk of foreclosure. |

This is the **proof-of-rigour moment**: the contradiction is grounded in the entity's *own* public
filing (cite-or-silence), so the CIO surfaces a cited contradicted crack that moves the robustness
verdict rather than averaging the disagreement away.

Secondary claims (CUDA/software moat, demand-exceeds-supply) are steelman-able and are *not* the
staged crack — they exist so the red-team has both contested and defensible ground to weigh.

## Notes
- **Clean-room / public framing only.** The thesis is a generic, public-information investment view;
  the corpus is public SEC filings (provenance in [`../knowledge/README.md`](../knowledge/README.md)).
- Whether the crack verifiably *flips* the verdict in a live run is checked in STORY-02.4.02 /
  STORY-05.2.01, not here — this fixture only guarantees the claim↔contradiction pairing exists.
