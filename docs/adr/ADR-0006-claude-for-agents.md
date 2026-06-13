# ADR-0006 — Claude for agent reasoning; Azure OpenAI (mini) for the planner

**Status:** Accepted · **Date:** 2026-06-12

## Context

The four agents need a reasoning model. The default assumption was Azure OpenAI `gpt-4o`. Two facts changed that: (1) the wider system (SoiKio) already runs on Anthropic Claude, and (2) `gpt-4o` quota on a cold Azure subscription can take days to grant — a deadline risk. Separately, Foundry IQ's agentic retrieval plans its sub-queries with an **Azure OpenAI** model, which is not substitutable.

## Decision

- **Agents (Bull/Bear/Caution/CIO) run on Claude** — via the Anthropic API (your key) or Claude deployed in Microsoft Foundry. Default `claude-sonnet-4-6`; Opus optional for the CIO.
- **The Foundry IQ query planner uses a small Azure OpenAI model** (e.g. `gpt-4o-mini`) — its only job is planning retrieval sub-queries.

## Consequences

- **+** Matches the team's existing Claude stack; one fewer model to learn.
- **+** Avoids the `gpt-4o` quota wait — only a *mini* Azure OpenAI deployment is needed (easier to obtain).
- **+** Still fully satisfies the track: the mandatory Microsoft IQ layer (Foundry IQ) is unchanged and Azure-native.
- **−** An **Azure subscription is still required** — Foundry IQ (AI Search + planner + Blob) is Azure-native regardless of the agent model. The Anthropic key only covers reasoning, not grounding.
- **−** Two model providers in play (Anthropic + Azure OpenAI). Acceptable: the planner is tiny and isolated to `foundry_iq.py`.
- Note: Claude-in-Foundry needs a paid Azure subscription billed in a Claude-supported region.

## Related

Model config lives in `.env` (`ANTHROPIC_API_KEY` / `CLAUDE_MODEL` / `AZURE_OPENAI_PLANNER_DEPLOYMENT`). Grounding requirement: ADR-0002. Resource footprint: `docs/runbook.md`, `SoiKio-Project/03-azure-architecture.md`.
