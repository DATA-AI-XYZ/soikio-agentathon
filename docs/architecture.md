# Architecture

**Red-team your investment thesis.** You submit a thesis; three stance agents test it against the public record (grounded by Foundry IQ); a CIO returns the **Kintsugi conflict map** — cracks gilded and ranked — plus a robustness verdict.

![Red-team architecture](architecture.svg)

## Agents

| Agent | Role |
|-------|------|
| **Bull** | Steelman the thesis — the strongest *cited* case it holds. |
| **Bear** | Attack the thesis — every claim the public record contradicts or can't support. |
| **Caution** | What *breaks* it — downside, base rates, data gaps, blind spots. Not a fence-sitter. |
| **CIO** | Build the Kintsugi conflict map (cracks ranked by severity) and rate robustness. |

Prompts: [`../prompts/`](../prompts/). Governing philosophy: the **Kintsugi Principle** — disagreement is signal, gild the cracks ([`kintsugi-principle.md`](kintsugi-principle.md)).

## The six lenses

Macro · Fundamental · Technical/Quant · Risk · Event-driven · Supply-chain. Each stance applies all six as its test surface — see [`../prompts/lenses.md`](../prompts/lenses.md).

## Grounding (Foundry IQ)

The public documents are the evidence the thesis is **tested against**. A **Foundry IQ knowledge base** returns extracts **with citations**, which makes cite-or-silence enforceable. Azure resources: [`azure-architecture.svg`](azure-architecture.svg).

## Flow

1. The user's thesis enters `src/agent.py`; claims are extracted.
2. Bull, Bear, Caution each test the claims per lens against cited evidence.
3. The CIO consolidates the cracks into the ranked conflict map and rates robustness (Holds / Contested / Breaks).
4. `src/citations.py` enforces cite-or-silence and blocks BUY/SELL/HOLD.

## Presentation

The cited brief is rendered as a **self-contained interactive HTML report** by `src/render.py` — deterministically, no model call — headlined by the Kintsugi conflict map, with a *debate / by-domain* view switch, an agent-run health panel, and click-to-expand citations. Spec: [`report-spec.md`](re