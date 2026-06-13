# ADR-0002 — Reasoning Agents track, grounded by Foundry IQ

**Status:** Accepted · **Date:** 2026-06-12

## Context

Agents League requires every submission to integrate at least one Microsoft IQ layer (Foundry IQ, Work IQ, or Fabric IQ) and to pick a track (Creative Apps / Reasoning Agents / Enterprise Agents). The deadline is 14 June 2026.

## Decision

Enter the **Reasoning Agents** track (build with Microsoft Foundry) and use **Foundry IQ** as the IQ layer.

## Consequences

- **+** Reasoning Agents is the natural fit for an investment-analysis debate.
- **+** Foundry IQ is **generally available now** and returns retrieval results *with citations*, which is exactly what makes cite-or-silence enforceable.
- **+** Foundry IQ runs on Azure AI Search with a **free tier** + free agentic-retrieval token allocation — near-zero PoC cost.
- **−** Ties the project to Azure provisioning; mitigated by keeping the resource set minimal (see `docs/runbook.md`).

## Alternatives considered

- **Work IQ** — its APIs go GA on **16 June 2026**, *after* the deadline. Rejected (dependency risk).
- **Fabric IQ** — strong for semantic business data, but heavier setup and less aligned to public-document grounding.
- **Enterprise Agents track (M365 Copilot)** — heavier, and leans on Work IQ timing.
