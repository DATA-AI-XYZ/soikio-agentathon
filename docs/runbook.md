# Runbook — provision & run

End-to-end setup for the debate on Azure. Confirm exact role names and SDK calls against the Foundry IQ connect-guide (linked below) while wiring the scripts.

## Prerequisites

- **Anthropic API key** for Claude (the agents) — or Claude deployed in Microsoft Foundry.
- Azure subscription with access to Microsoft Foundry (New Foundry).
- `az` CLI logged in (`az login`) — used by `DefaultAzureCredential`.
- Python 3.11+.

## 1. Provision resources

Either via the Foundry portal (fastest) or IaC. Minimum set:

1. **Microsoft Foundry project** (Foundry Agent Service).
2. **Azure AI Search** service — tier that supports **agentic retrieval** (free tier is fine for the demo).
3. **Azure OpenAI** deployment — a **small** model (e.g. `gpt-4o-mini`) used **only** as the Foundry IQ query planner. The agents themselves run on **Claude** (Anthropic key or Claude-in-Foundry), so no large `gpt-4o` quota is needed.
4. **Azure Storage account** + a Blob container (`public-docs`) for the knowledge source.

## 2. Identity & RBAC

Grant the Foundry project's **managed identity** (indicative — confirm in connect-guide):

- *Search Index Data Reader* (+ *Search Service Contributor* during setup) on Azure AI Search.
- *Storage Blob Data Reader* on the Blob container.
- *Cognitive Services OpenAI User* on the Azure OpenAI deployment.

## 3. Load public documents

Upload the documents in [`../knowledge/`](../knowledge/) to the Blob container. Keep the set small (a few filings) — faster indexing, cheaper, easier to demo. Record provenance in `knowledge/README.md`.

## 4. Configure

```bash
cp .env.example .env     # fill endpoints; do NOT add secrets — use managed identity
pip install -r requirements.txt
```

## 5. Build the knowledge base

```bash
python scripts/setup_foundry_iq.py
```

Creates the Foundry IQ knowledge base, adds the Blob knowledge source, indexes the documents, and sets retrieval parameters (`RETRIEVAL_REASONING_EFFORT`).

## 6. Run the debate

```bash
python scripts/run_example.py --thesis examples/thesis.txt
```

Extracts claims, runs Bull, Bear, Caution, then the CIO; prints/saves the cited brief headlined by the conflict map (schema in `output-schema.md`).

## 7. Verify

Run the checks in [`evaluation.md`](evaluation.md) before recording the demo.

## References

- What is Foundry IQ? — https://learn.microsoft.com/en-us/azure/foundry/agents/concepts/what-is-foundry-iq
- Co