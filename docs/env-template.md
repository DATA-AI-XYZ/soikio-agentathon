# `.env` template (canonical)

The repo's `.env.example` is permission-protected, so this is the maintained, comprehensive template.
**Copy the block below into `.env`** (or `.env.example`) and fill the placeholders. Most values are
**outputs of `infra/main.bicep`** — the deploy script writes them automatically. Order: Bicep →
capture `.env` → `setup_foundry_iq.py`. Verified against Microsoft Learn 2026-06-13. See
[`azure-resources.md`](./azure-resources.md). Decisions: ADR-0010, ADR-0011.

```dotenv
# ===== Claude (the four agents) — LOCAL DEV key only; prod key comes from Key Vault =====
ANTHROPIC_API_KEY=sk-ant-...
CLAUDE_MODEL=claude-sonnet-4-6
CLAUDE_CIO_MODEL=claude-opus-4-8

# ===== Key Vault (production secret path) =====
KEY_VAULT_URI=https://<your-kv>.vault.azure.net/
ANTHROPIC_SECRET_NAME=anthropic-api-key

# ===== Identity / tenant (keyless via DefaultAzureCredential) =====
AZURE_CLIENT_ID=<uami-client-id>
AZURE_TENANT_ID=<tenant-guid>

# ===== Azure AI Search (Foundry IQ agentic retrieval — Basic tier+) =====
AZURE_SEARCH_ENDPOINT=https://<your-search>.search.windows.net
AZURE_SEARCH_KNOWLEDGE_BASE=REDACTED-kb
AZURE_SEARCH_KNOWLEDGE_SOURCE=REDACTED-docs
AZURE_SEARCH_API_VERSION=2026-05-01-preview
AZURE_SEARCH_OUTPUT_MODE=extractedData
RETRIEVAL_REASONING_EFFORT=low

# ===== Azure OpenAI — TWO small deployments (not the agents) =====
AZURE_OPENAI_ENDPOINT=https://<your-openai>.openai.azure.com
AZURE_OPENAI_PLANNER_DEPLOYMENT=gpt-4o-mini
AZURE_OPENAI_EMBEDDING_DEPLOYMENT=text-embedding-3-large

# ===== Storage (public docs) =====
AZURE_STORAGE_ACCOUNT=<your-storage-account>
AZURE_STORAGE_CONTAINER=public-docs

# ===== Observability =====
APPLICATIONINSIGHTS_CONNECTION_STRING=InstrumentationKey=...;IngestionEndpoint=...

# ===== Hosting (infra; handy for deploy scripts) =====
ACR_LOGIN_SERVER=<your-acr>.azurecr.io
CONTAINER_APP_NAME=<your-container-app>

# ===== Foundry project (OPTIONAL — runtime uses direct KB retrieve, ADR-0011) =====
# FOUNDRY_PROJECT_ENDPOINT=https://<your-project>.services.ai.azure.com/api/projects/<project-name>
```

## What changed vs the old `.env.example`
New / corrected variables this foundation work added:
- `CLAUDE_CIO_MODEL` — optional Opus for the CIO.
- `KEY_VAULT_URI`, `ANTHROPIC_SECRET_NAME` — production secret path (ADR-0010).
- `AZURE_CLIENT_ID` — the managed identity's clientId for `DefaultAzureCredential`.
- `AZURE_SEARCH_KNOWLEDGE_SOURCE`, `AZURE_SEARCH_API_VERSION`, `AZURE_SEARCH_OUTPUT_MODE` — agentic-retrieval specifics.
- **`AZURE_OPENAI_EMBEDDING_DEPLOYMENT`** — required by the knowledge source for vectorisation (was missing).
- `APPLICATIONINSIGHTS_CONNECTION_STRING`, `ACR_LOGIN_SERVER`, `CONTAINER_APP_NAME` — observability + hosting.
