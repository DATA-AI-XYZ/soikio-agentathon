# Storage for historical runs — Azure deploy

Persist every red-team run (thesis + conflict map + citations) to Azure so past analyses are stored and **accessible historically**. Uses the `BlobStore` backend already in `src/memory.py` — no code change, just provisioning + config. Maps to **EPIC-07 (production hardening, audit-grade)**.

## Option A — Azure Blob (recommended now: reuse the existing Storage account)

The contest build already provisions a Storage account (EPIC-00/06). Add a container, grant the app access, flip one env var.

```bash
ACCT=<your-storage-account>; RG=<your-rg>; APP=<your-container-app>

# 1. Create the runs container
az storage container create --account-name "$ACCT" --name runs --auth-mode login

# 2. Grant the Container App's managed identity read/write on Blob
PRINCIPAL=$(az containerapp show -n "$APP" -g "$RG" --query identity.principalId -o tsv)
SCOPE=$(az storage account show -n "$ACCT" -g "$RG" --query id -o tsv)
az role assignment create \
  --assignee-object-id "$PRINCIPAL" --assignee-principal-type ServicePrincipal \
  --role "Storage Blob Data Contributor" --scope "$SCOPE"

# 3. Point the app at Blob (env vars on the Container App)
az containerapp update -n "$APP" -g "$RG" \
  --set-env-vars MEMORY_BACKEND=blob AZURE_STORAGE_ACCOUNT="$ACCT" MEMORY_CONTAINER=runs
```

`memory.py` → `BlobStore` now writes each run as `runs/<run_id>.json` with `overwrite=False` (append-only — a run id is never silently replaced).

## Make it audit-grade (immutability) — the COMPLIANCE-CRITICAL bit

```bash
# blob versioning
az storage account blob-service-properties update --account-name "$ACCT" --enable-versioning true
```
Then set a **time-based immutability (WORM) policy** on the `runs` container (portal: Container → Access policy → Add immutability policy, or via CLI) so a stored brief can't be altered or deleted within the retention window. That turns the run store into a tamper-evident audit trail.

## Accessing historical runs

- **API** — expose `GET /api/runs` (list) and `GET /api/runs/{id}` (fetch), backed by `memory.list_runs()` / `get_run()`.
- **UI** — add a **History** view to `web/` that calls `/api/runs` and re-renders past conflict maps with the existing report renderer.
- **Reflection** — `memory.prior_run(ticker)` returns the latest brief for an entity (the resolution-loop "what changed" seed).
- **Direct/ops** — `az storage blob list --account-name "$ACCT" -c runs --auth-mode login`, or browse in the portal.

## Local ↔ cloud switch (no code change)

| Env | Backend | Where runs go |
|-----|---------|---------------|
| `MEMORY_BACKEND` unset | `LocalJsonStore` | `./runs/*.json` (offline dev/demo) |
| `MEMORY_BACKEND=blob` | `BlobStore` | Azure Blob `runs` container |

## Production upgrade — Cosmos / PostgreSQL (EPIC-07 target)

Blob is ideal for the **document** (the immutable brief JSON). For rich history *queries* — by ticker, date, verdict, across users — add **Cosmos DB or Azure Database for PostgreSQL** as the index: keep the brief blob as the immutable artefact, store metadata + a blob pointer in the DB for fast lookup. `memory.py`'s interface (`save/get/list/prior_run`) stays the same — you implement a third `MemoryStore` and swap `get_store()`. This is the audit-trail DB in [`../_00-Project-Management/20-Requirements/SPEC-production-azure-architecture.md`](../_00-Project-Management/20-Requirements/SPEC-production-azure-architecture.md).

## Don't do this before submission
This is a post-submission hardening step (EPIC-07). For the contest, `LocalJsonStore` already demonstrates memory end-to-end; flipping to Blob is a config change you can make after the deadline without touching the green build.
