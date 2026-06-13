# ADR-0005 — Deterministic HTML renderer, not a formatting agent

**Status:** Accepted · **Date:** 2026-06-12

## Context

The output is most useful as a readable, interactive HTML brief (UX & Presentation, 15%). A natural question was whether to add a fifth agent to format the CIO's output into HTML.

## Decision

Render the report with a **deterministic template** (`src/render.py`) that consumes the validated CIO JSON and emits a self-contained interactive HTML file. **No LLM is used for presentation.**

## Consequences

- **+** Guarantees **cite-or-silence**: a template cannot paraphrase a figure or drop a citation; an LLM formatter could.
- **+** Zero token cost, near-zero latency, one fewer failure point.
- **+** Output is reproducible — same brief in, same HTML out.
- **+** The renderer enforces invariants (no BUY/SELL; uncited figures stripped; empty lenses shown as "thin", not omitted).
- **−** Layout changes mean editing a template rather than re-prompting — a feature, not a bug, for reliability.

## Alternatives considered

- *Formatting agent* — rejected: adds a fabrication surface over the exact data that must stay verbatim, plus cost/latency/fragility.
- *Raw JSON only* — rejected: poor presentation, weak for the demo and judges.

## Related

Presentation layer sits **after** the CIO, outside the reasoning path. Spec: `docs/report-spec.md`. Sample: `docs/report.sample.html`.
