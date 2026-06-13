# ADR-0003 — Clean-room build on public data only

**Status:** Accepted · **Date:** 2026-06-12

## Context

The method behind this project is distilled from an internal, proprietary multi-agent investment-research system. The Agents League submission repository must be **public**, and the event disclaimer forbids uploading confidential information.

## Decision

Build **clean-room**: this repository re-expresses only the *method and ideas* (which we own) in freshly-written, generic form, and uses **public data only**. It contains **no** proprietary prompts, no proprietary agent-to-domain mappings, no proprietary weighting or thresholds, and no private data.

## Consequences

- **+** No confidentiality exposure; safe to make public.
- **+** Keeps the proprietary system's IP intact and separate.
- **−** Cannot reuse the existing prompts/code directly — everything in `prompts/` is written fresh.
- **−** Requires a discipline gate: a review of every file before the repo is flipped public.

## Enforcement

- Reference prompts from the internal system are kept **outside** this repository and are never committed.
- `knowledge/` holds only public documents, each with recorded provenance.
- A pre-submission clean-room check scans for any proprietary content. See `COMPLIANCE.md`.
