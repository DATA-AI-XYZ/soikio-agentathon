# Compliance & Safety

This project is an entry to **Agents League @ AISF 2026** and adheres to the event's Disclaimer, Code of Conduct, and Security Policy.

## No confidential information

This repository contains **public data only**. All documents used as knowledge sources are publicly available, with their provenance recorded in [`knowledge/README.md`](knowledge/README.md). No confidential, proprietary, or personal data is present.

## Clean-room

The analytical *method* draws on an internal multi-agent research system, but this repository is a **clean-room re-implementation**: it contains no proprietary prompts, no proprietary agent-to-domain mappings, no proprietary weighting or thresholds, and no private data. All prompts in `prompts/` are written fresh and generically for this project.

## Analysis, not investment advice

This tool produces **analytical commentary**, not investment advice or a recommendation to transact.

- Verdicts use an analytical family — **Bullish / Caution / Bearish** — with a confidence score.
- The system **never** emits BUY / SELL / HOLD instructions; `src/citations.py` blocks such language.
- Outputs may be incomplete or wrong, are limited to the documents provided, and must not be relied upon for financial decisions. Not regulated financial advice.

## Reliability guards

- **Cite-or-silence:** every figure must trace to a retrieved source; unsupported claims are dropped or flagged.
- **Grounded retrieval:** facts come from Foundry IQ over the supplied public documents, not from model memory.
- **Surfaced uncertainty:** disagreement between stances and low-confidence findings are reported, not hidden.

## Secrets

No secrets are committed. Configuration uses `.env` (git-ignored); authentication prefers managed identity / `DefaultAzureCredential`.
