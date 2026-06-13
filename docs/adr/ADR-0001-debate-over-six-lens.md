# ADR-0001 — Adversarial debate over a single six-lens agent

**Status:** Accepted · **Date:** 2026-06-12

## Context

The entry needs to demonstrate multi-step reasoning (rubric 20%) and originality (15%) while shipping in two days. An early design had one agent reasoning across six analytical lenses and synthesising a verdict. It was sound but flat: the reasoning happened inside one pass and was hard to make legible in a 3-minute demo.

## Decision

Restructure as a **structured adversarial debate**: three stance agents — **Bull**, **Bear**, **Caution** — each argue across the six lenses, and a **CIO** agent adjudicates and writes the cited brief. The six lenses are retained as each stance's internal evidence checklist.

## Consequences

- **+** Reasoning becomes visible and inspectable — three argued cases plus an adjudication step.
- **+** "Conflict is signal" becomes structural: disagreement is the mechanism, not an afterthought.
- **+** A debate is a legible story for the demo video (helps UX/Presentation, 15%).
- **+** The three stances map cleanly onto the verdict family (see ADR-0004).
- **−** More model calls than a single agent (4 vs 1) — acceptable for a one-ticker demo; watch cost at scale.
- **−** Single-pass debate (no multi-round rebuttal) — noted as a future extension.

## Alternatives considered

- *Single six-lens agent* — simpler, but less legible and less original.
- *Full multi-agent system (many specialists)* — too large to build and demo in two days; also closer to the proprietary system we are deliberately not reproducing (ADR-0003).
