# ADR-0004 — Verdict family Bullish/Caution/Bearish; no BUY/SELL

**Status:** Accepted · **Date:** 2026-06-12

## Context

The system produces directional assessments of equities. Emitting BUY/SELL/HOLD instructions would frame the output as investment advice, raising regulatory and safety concerns and weakening the "analysis, not advice" stance the project is built on.

## Decision

Outputs use an **analytical verdict family — Bullish / Caution / Bearish** — with a confidence score. The strings **BUY / SELL / HOLD are forbidden** anywhere in agent or final output. A guard in `src/citations.py` rejects them.

The three debate stances map onto this family: Bull→Bullish, Bear→Bearish, Caution→Caution (the balanced / risk-dominated / low-confidence outcome).

## Consequences

- **+** Keeps the project clearly on the analysis side of the advice line (supports Reliability & Safety, 20%).
- **+** Clean conceptual mapping from the debate to the verdict.
- **+** `Caution` gives the CIO an honest option when evidence doesn't support a lean — no forced decisiveness.
- **−** Users wanting a transactional call won't get one — intended.

## Related

Enforced alongside **cite-or-silence** (no invented numbers) — see `prompts/system.md` and `docs/output-schema.md` invariants.
