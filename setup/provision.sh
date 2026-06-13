#!/usr/bin/env bash
#
# provision.sh — one-command Azure provisioning for soikio-agentathon (STORY-01.1.01)
#
# Provisions the grounding-layer infrastructure with least-privilege RBAC:
#   1. Resource group
#   2. Azure Storage account + Blob container (public-docs)  + uploads knowledge/ docs
#   3. Azure AI Search service (Basic tier by default — see SEARCH_SKU note below)
#   4. Microsoft Foundry resource (kind=AIServices) + Foundry project
#   5. gpt-4o-mini deployment on the Foundry resource (the Foundry IQ query planner)
#   6. Managed-identity RBAC wiring across the above
#
# It does NOT build the Foundry IQ knowledge base — that is scripts/setup_foundry_iq.py
# (Python SDK, control-plane API must be verified against Microsoft Learn first; see
# setup/CLAUDE.md §7). This script stops at infrastructure + RBAC + document upload.
#
# Idempotent: every step checks for existing resources before creating. Safe to re-run.
#
# ── Prerequisites ────────────────────────────────────────────────────────────
#   • az CLI >= 2.51.0, logged in:  az login  (az account set --subscription <id>)
#   • Owner/Contributor + User Access Administrator on the target subscription (for RBAC)
#   • gpt-4o-mini quota granted in $LOCATION  (this is the deadline-critical blocker —
#     see _00-Project-Management/10-Inbox/quota-region-verification.md). The script
#     PRE-CHECKS quota and stops early with guidance if it is zero.
#
# ── Usage ────────────────────────────────────────────────────────────────────
#   bash setup/provision.sh              # provision everything, print .env values
#   bash setup/provision.sh --dry-run    # print the plan, create nothing
#   bash setup/provision.sh --write-env  # also write endpoints into ../.env
#
#   Override any default via environment, e.g.:
#     LOCATION=westus3 NAME_PREFIX=soikio SEARCH_SKU=basic bash setup/provision.sh
#
# ── SEARCH_SKU note ──────────────────────────────────────────────────────────
#   Defaults to "basic". Agentic retrieval requires Basic tier or higher because the
#   FREE search tier does NOT support managed identity, and this project authenticates
#   keyless via DefaultAzureCredential. Setting SEARCH_SKU=free will provision a free
#   service but the managed-identity RBAC step is unsupported and will be SKIPPED with
#   a warning — you would then need admin-key auth instead. (STORY-01.1.01 AC2.)
#
set -euo pipefail

# ── Configuration (override via env) ─────────────────────────────────────────
LOCATION="${LOCATION:-eastus2}"
NAME_PREFIX="${NAME_PREFIX:-soikio}"
RESOURCE_GROUP="${RESOURCE_GROUP:-rg-${NAME_PREFIX}-agentathon}"
SEARCH_SKU="${SEARCH_SKU:-basic}"            # basic | standard | free (free => no managed identity)
PLANNER_MODEL="${PLANNER_MODEL:-gpt-4o-mini}"
PLANNER_DEPLOYMENT="${PLANNER_DEPLOYMENT:-gpt-4o-mini}"
PLANNER_CAPACITY="${PLANNER_CAPACITY:-30}"   # K tokens/min for the deployment
CONTAINER="${AZURE_STORAGE_CONTAINER:-public-docs}"
KNOWLEDGE_DIR="${KNOWLEDGE_DIR:-$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)/knowledge}"
ENV_FILE="${ENV_FILE:-$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)/.env}"

DRY_RUN=false
WRITE_ENV=false
for arg in "$@"; do
  case "$arg" in
    --dry-run)   DRY_RUN=true ;;
    --write-env) WRITE_ENV=true ;;
    -h|--help)   sed -n '2,55p' "${BASH_SOURCE[0]}" | sed 's/^# \{0,1\}//'; exit 0 ;;
    *) echo "Unknown argument: $arg (try --help)" >&2; exit 2 ;;
  esac
done

# ── Pretty logging ───────────────────────────────────────────────────────────
c_blue=$'\033[34m'; c_green=$'\033[32m'; c_yellow=$'\033[33m'; c_red=$'\033[31m'; c_dim=$'\033[2m'; c_off=$'\033[0m'
step() { echo "${c_blue}▶ $*${c_off}"; }
ok()   { echo "${c_green}  ✓ $*${c_off}"; }
warn() { echo "${c_yellow}  ⚠ $*${c_off}"; }
die()  { echo "${c_red}  ✗ $*${c_off}" >&2; exit 1; }
run()  { if $DRY_RUN; then echo "${c_dim}  [dry-run] $*${c_off}"; else eval "$@"; fi; }

command -v az >/dev/null 2>&1 || die "az CLI not found. Install: https://learn.microsoft.com/cli/azure/install-azure-cli"

# ── Resolve subscription + identity ──────────────────────────────────────────
step "Checking az login"
az account show -o none 2>/dev/null || die "Not logged in. Run: az login"
SUBSCRIPTION_ID="${AZURE_SUBSCRIPTION_ID:-$(az account show --query id -o tsv 2>/dev/null)}"
[ -n "$SUBSCRIPTION_ID" ] || die "Could not resolve subscription id."
az account set --subscription "$SUBSCRIPTION_ID"
CURRENT_USER_OID="$(az ad signed-in-user show --query id -o tsv 2>/dev/null || true)"
ok "Subscription: $SUBSCRIPTION_ID"

# Deterministic, globally-unique-ish suffix (stable across re-runs for idempotency)
SUFFIX="$(printf '%s' "${SUBSCRIPTION_ID}${NAME_PREFIX}" | sha1sum | cut -c1-6)"
STORAGE_ACCOUNT="${AZURE_STORAGE_ACCOUNT:-${NAME_PREFIX}${SUFFIX}sa}"   # 3–24 lowercase alnum
SEARCH_SERVICE="${SEARCH_SERVICE:-${NAME_PREFIX}-search-${SUFFIX}}"
FOUNDRY_RESOURCE="${FOUNDRY_RESOURCE:-${NAME_PREFIX}-foundry-${SUFFIX}}"
FOUNDRY_PROJECT="${FOUNDRY_PROJECT:-${NAME_PREFIX}-project}"

echo
echo "${c_dim}── Plan ──────────────────────────────────────────────${c_off}"
cat <<PLAN
  Location ........... $LOCATION
  Resource group ..... $RESOURCE_GROUP
  Storage account .... $STORAGE_ACCOUNT   (container: $CONTAINER)
  AI Search .......... $SEARCH_SERVICE   (sku: $SEARCH_SKU)
  Foundry resource ... $FOUNDRY_RESOURCE
  Foundry project .... $FOUNDRY_PROJECT
  Planner model ...... $PLANNER_MODEL  ->  deployment "$PLANNER_DEPLOYMENT" (${PLANNER_CAPACITY}K TPM)
  Knowledge dir ...... $KNOWLEDGE_DIR
PLAN
echo "${c_dim}──────────────────────────────────────────────────────${c_off}"
echo

if [ "$SEARCH_SKU" = "free" ]; then
  warn "SEARCH_SKU=free: managed identity is UNSUPPORTED on the free search tier."
  warn "The RBAC stage will be skipped; you must use admin-key auth instead. (STORY-01.1.01 AC2 expects Basic+.)"
fi

# ── 0. Register resource providers ───────────────────────────────────────────
step "Registering resource providers"
for ns in Microsoft.CognitiveServices Microsoft.Search Microsoft.Storage; do
  state="$(az provider show --namespace "$ns" --query registrationState -o tsv 2>/dev/null || echo NotRegistered)"
  if [ "$state" != "Registered" ]; then
    run "az provider register --namespace $ns --wait"
    ok "Registered $ns"
  else
    ok "$ns already registered"
  fi
done

# ── 1. Resource group ────────────────────────────────────────────────────────
step "Resource group: $RESOURCE_GROUP"
if az group show -n "$RESOURCE_GROUP" >/dev/null 2>&1; then
  ok "Already exists"
else
  run "az group create -n $RESOURCE_GROUP -l $LOCATION -o none"
  ok "Created"
fi

# ── 2. Storage account + container ───────────────────────────────────────────
step "Storage account: $STORAGE_ACCOUNT"
if az storage account show -n "$STORAGE_ACCOUNT" -g "$RESOURCE_GROUP" >/dev/null 2>&1; then
  ok "Already exists"
else
  run "az storage account create -n $STORAGE_ACCOUNT -g $RESOURCE_GROUP -l $LOCATION \
        --sku Standard_LRS --kind StorageV2 --min-tls-version TLS1_2 \
        --allow-blob-public-access false -o none"
  ok "Created"
fi
step "Blob container: $CONTAINER"
if $DRY_RUN; then
  echo "${c_dim}  [dry-run] az storage container create --name $CONTAINER ...${c_off}"
else
  az storage container create --name "$CONTAINER" --account-name "$STORAGE_ACCOUNT" \
    --auth-mode login -o none 2>/dev/null \
    || az storage container create --name "$CONTAINER" --account-name "$STORAGE_ACCOUNT" -o none
  ok "Ready"
fi

# ── 3. Azure AI Search ───────────────────────────────────────────────────────
step "Azure AI Search: $SEARCH_SERVICE (sku=$SEARCH_SKU)"
SEARCH_IDENTITY_ARG=""
[ "$SEARCH_SKU" != "free" ] && SEARCH_IDENTITY_ARG="--identity-type SystemAssigned"
if az search service show --name "$SEARCH_SERVICE" -g "$RESOURCE_GROUP" >/dev/null 2>&1; then
  ok "Already exists"
else
  run "az search service create --name $SEARCH_SERVICE -g $RESOURCE_GROUP -l $LOCATION \
        --sku $SEARCH_SKU $SEARCH_IDENTITY_ARG -o none"
  ok "Created"
fi

# ── 4. Foundry resource (AIServices) + project ───────────────────────────────
step "Foundry resource: $FOUNDRY_RESOURCE (kind=AIServices)"
if az cognitiveservices account show -n "$FOUNDRY_RESOURCE" -g "$RESOURCE_GROUP" >/dev/null 2>&1; then
  ok "Already exists"
else
  run "az cognitiveservices account create -n $FOUNDRY_RESOURCE -g $RESOURCE_GROUP -l $LOCATION \
        --kind AIServices --sku S0 --custom-domain $FOUNDRY_RESOURCE \
        --allow-project-management true --assign-identity --yes -o none"
  ok "Created"
fi

step "Foundry project: $FOUNDRY_PROJECT"
if az cognitiveservices account project show --name "$FOUNDRY_RESOURCE" -g "$RESOURCE_GROUP" \
     --project-name "$FOUNDRY_PROJECT" >/dev/null 2>&1; then
  ok "Already exists"
else
  run "az cognitiveservices account project create --name $FOUNDRY_RESOURCE -g $RESOURCE_GROUP \
        --project-name $FOUNDRY_PROJECT --location $LOCATION -o none"
  ok "Created"
fi

# ── 5. gpt-4o-mini deployment (Foundry IQ query planner) ─────────────────────
step "Quota pre-check for $PLANNER_MODEL in $LOCATION"
if $DRY_RUN; then
  echo "${c_dim}  [dry-run] az cognitiveservices usage list -l $LOCATION${c_off}"
else
  USAGE_JSON="$(az cognitiveservices usage list -l "$LOCATION" -o json 2>/dev/null || echo '[]')"
  # Look for any quota line mentioning the planner model with a non-zero limit.
  LIMIT="$(printf '%s' "$USAGE_JSON" | python - "$PLANNER_MODEL" <<'PY' 2>/dev/null || echo "unknown"
import sys, json
model = sys.argv[1].lower()
try:
    data = json.load(sys.stdin)
except Exception:
    print("unknown"); sys.exit()
best = 0; found = False
for u in data:
    name = (u.get("name", {}) or {}).get("value", "") if isinstance(u.get("name"), dict) else str(u.get("name", ""))
    if model.replace("-", "") in name.lower().replace("-", ""):
        found = True
        try: best = max(best, float(u.get("limit", 0)))
        except Exception: pass
print(int(best) if found else "unknown")
PY
)"
  if [ "$LIMIT" = "unknown" ]; then
    warn "Could not read $PLANNER_MODEL quota automatically — proceeding; deployment will fail loudly if quota is 0."
  elif [ "$LIMIT" = "0" ]; then
    die "No $PLANNER_MODEL quota in $LOCATION (limit=0). Request quota (lead time can be days — see 10-Inbox/quota-region-verification.md) or set LOCATION to a region where you have quota, then re-run."
  else
    ok "Quota available (limit≈${LIMIT}K TPM)"
  fi
fi

step "Resolving available $PLANNER_MODEL version + sku"
if $DRY_RUN; then
  MODEL_VERSION="<auto>"; MODEL_SKU="GlobalStandard"
  echo "${c_dim}  [dry-run] az cognitiveservices account list-models ...${c_off}"
else
  read -r MODEL_VERSION MODEL_SKU < <(
    az cognitiveservices account list-models -n "$FOUNDRY_RESOURCE" -g "$RESOURCE_GROUP" -o json 2>/dev/null \
    | python - "$PLANNER_MODEL" <<'PY' 2>/dev/null || true
import sys, json
model = sys.argv[1].lower()
data = json.load(sys.stdin)
cands = [m for m in data if m.get("name", "").lower() == model and m.get("format") == "OpenAI"]
if not cands:
    cands = [m for m in data if model in m.get("name", "").lower()]
if not cands:
    sys.exit()
# newest version, prefer GlobalStandard then Standard
cands.sort(key=lambda m: m.get("version", ""), reverse=True)
m = cands[0]
skus = [s.get("name") for s in m.get("skus", [])]
sku = "GlobalStandard" if "GlobalStandard" in skus else ("Standard" if "Standard" in skus else (skus[0] if skus else "GlobalStandard"))
print(m.get("version", ""), sku)
PY
  )
  MODEL_SKU="${MODEL_SKU:-GlobalStandard}"
  if [ -z "${MODEL_VERSION:-}" ]; then
    warn "Could not auto-detect $PLANNER_MODEL version; falling back to model default."
  else
    ok "Using version=$MODEL_VERSION sku=$MODEL_SKU"
  fi
fi

step "Model deployment: $PLANNER_DEPLOYMENT"
if az cognitiveservices account deployment show -n "$FOUNDRY_RESOURCE" -g "$RESOURCE_GROUP" \
     --deployment-name "$PLANNER_DEPLOYMENT" >/dev/null 2>&1; then
  ok "Already exists"
else
  VERSION_ARG=""; [ -n "${MODEL_VERSION:-}" ] && [ "${MODEL_VERSION}" != "<auto>" ] && VERSION_ARG="--model-version $MODEL_VERSION"
  run "az cognitiveservices account deployment create -n $FOUNDRY_RESOURCE -g $RESOURCE_GROUP \
        --deployment-name $PLANNER_DEPLOYMENT \
        --model-name $PLANNER_MODEL $VERSION_ARG --model-format OpenAI \
        --sku-name ${MODEL_SKU:-GlobalStandard} --sku-capacity $PLANNER_CAPACITY -o none"
  ok "Deployed"
fi

# ── 6. RBAC wiring (managed identity, least privilege) ───────────────────────
ensure_role() {  # $1=assignee-object-id  $2=role  $3=scope
  local oid="$1" role="$2" scope="$3"
  [ -z "$oid" ] && { warn "skip role '$role' (no principal id)"; return; }
  if $DRY_RUN; then echo "${c_dim}  [dry-run] role '$role' -> $oid @ ${scope##*/}${c_off}"; return; fi
  if az role assignment list --assignee "$oid" --role "$role" --scope "$scope" \
       --query "[0].id" -o tsv 2>/dev/null | grep -q .; then
    ok "role '$role' already assigned"
  else
    az role assignment create --assignee-object-id "$oid" --assignee-principal-type ServicePrincipal \
      --role "$role" --scope "$scope" -o none 2>/dev/null \
      && ok "role '$role' assigned" \
      || warn "could not assign '$role' (need User Access Administrator?) — assign manually"
  fi
}

if [ "$SEARCH_SKU" = "free" ]; then
  warn "Skipping managed-identity RBAC (free search tier has no managed identity)."
else
  step "RBAC wiring"
  STORAGE_ID="$(az storage account show -n "$STORAGE_ACCOUNT" -g "$RESOURCE_GROUP" --query id -o tsv 2>/dev/null || true)"
  SEARCH_ID="$(az search service show --name "$SEARCH_SERVICE" -g "$RESOURCE_GROUP" --query id -o tsv 2>/dev/null || true)"
  FOUNDRY_ID="$(az cognitiveservices account show -n "$FOUNDRY_RESOURCE" -g "$RESOURCE_GROUP" --query id -o tsv 2>/dev/null || true)"
  SEARCH_OID="$(az search service show --name "$SEARCH_SERVICE" -g "$RESOURCE_GROUP" --query identity.principalId -o tsv 2>/dev/null || true)"
  FOUNDRY_OID="$(az cognitiveservices account show -n "$FOUNDRY_RESOURCE" -g "$RESOURCE_GROUP" --query identity.principalId -o tsv 2>/dev/null || true)"

  # Search service identity → read blobs + call the planner model (agentic retrieval path)
  ensure_role "$SEARCH_OID" "Storage Blob Data Reader"        "$STORAGE_ID"
  ensure_role "$SEARCH_OID" "Cognitive Services OpenAI User"  "$FOUNDRY_ID"
  # Foundry/agent identity → query the search index + read blobs (per STORY-01.1.01)
  ensure_role "$FOUNDRY_OID" "Search Index Data Reader"       "$SEARCH_ID"
  ensure_role "$FOUNDRY_OID" "Storage Blob Data Reader"       "$STORAGE_ID"
  ensure_role "$FOUNDRY_OID" "Cognitive Services OpenAI User" "$FOUNDRY_ID"

  # The human/CI principal running setup_foundry_iq.py → create the KB + upload docs
  if [ -n "$CURRENT_USER_OID" ] && ! $DRY_RUN; then
    for r in "Search Service Contributor" "Search Index Data Contributor"; do
      az role assignment create --assignee-object-id "$CURRENT_USER_OID" --assignee-principal-type User \
        --role "$r" --scope "$SEARCH_ID" -o none 2>/dev/null && ok "you → '$r'" || warn "could not grant you '$r'"
    done
    az role assignment create --assignee-object-id "$CURRENT_USER_OID" --assignee-principal-type User \
      --role "Storage Blob Data Contributor" --scope "$STORAGE_ID" -o none 2>/dev/null \
      && ok "you → 'Storage Blob Data Contributor'" || warn "could not grant you blob-contributor"
  fi
fi

# ── 7. Upload public documents ───────────────────────────────────────────────
step "Uploading public documents from $KNOWLEDGE_DIR"
if [ ! -d "$KNOWLEDGE_DIR" ]; then
  warn "No knowledge dir — skipping upload."
else
  DOC_COUNT="$(find "$KNOWLEDGE_DIR" -maxdepth 1 -type f ! -iname 'README.md' | wc -l | tr -d ' ')"
  if [ "$DOC_COUNT" = "0" ]; then
    warn "No documents to upload (only README). Add public filings to knowledge/ and re-run, or upload via setup_foundry_iq.py."
  elif $DRY_RUN; then
    echo "${c_dim}  [dry-run] upload $DOC_COUNT file(s) to $CONTAINER${c_off}"
  else
    az storage blob upload-batch -d "$CONTAINER" -s "$KNOWLEDGE_DIR" \
      --account-name "$STORAGE_ACCOUNT" --auth-mode login --overwrite \
      --pattern "*" --exclude-pattern "README.md" -o none \
      && ok "Uploaded $DOC_COUNT document(s)" \
      || warn "Upload failed (RBAC may still be propagating — retry in a minute)."
  fi
fi

# ── 8. Emit .env values ──────────────────────────────────────────────────────
if ! $DRY_RUN; then
  FOUNDRY_ACCT_ENDPOINT="$(az cognitiveservices account show -n "$FOUNDRY_RESOURCE" -g "$RESOURCE_GROUP" --query properties.endpoint -o tsv 2>/dev/null || true)"
fi
FOUNDRY_PROJECT_ENDPOINT="https://${FOUNDRY_RESOURCE}.services.ai.azure.com/api/projects/${FOUNDRY_PROJECT}"
AZURE_OPENAI_ENDPOINT="${FOUNDRY_ACCT_ENDPOINT:-https://${FOUNDRY_RESOURCE}.openai.azure.com}"
AZURE_SEARCH_ENDPOINT="https://${SEARCH_SERVICE}.search.windows.net"
TENANT_ID="$(az account show --query tenantId -o tsv 2>/dev/null || echo '<tenant-guid>')"

echo
echo "${c_green}══ Provisioning complete ══${c_off}"
echo "Paste these into ${ENV_FILE} (endpoints only — no secrets):"
echo "${c_dim}────────────────────────────────────────────────────${c_off}"
ENV_BLOCK="$(cat <<ENV
FOUNDRY_PROJECT_ENDPOINT=${FOUNDRY_PROJECT_ENDPOINT}
AZURE_SEARCH_ENDPOINT=${AZURE_SEARCH_ENDPOINT}
AZURE_OPENAI_ENDPOINT=${AZURE_OPENAI_ENDPOINT}
AZURE_OPENAI_PLANNER_DEPLOYMENT=${PLANNER_DEPLOYMENT}
AZURE_STORAGE_ACCOUNT=${STORAGE_ACCOUNT}
AZURE_STORAGE_CONTAINER=${CONTAINER}
AZURE_TENANT_ID=${TENANT_ID}
ENV
)"
echo "$ENV_BLOCK"
echo "${c_dim}────────────────────────────────────────────────────${c_off}"

if $WRITE_ENV && ! $DRY_RUN; then
  [ -f "$ENV_FILE" ] || { [ -f "${ENV_FILE%/*}/.env.example" ] && cp "${ENV_FILE%/*}/.env.example" "$ENV_FILE"; }
  while IFS='=' read -r key val; do
    [ -z "$key" ] && continue
    if [ -f "$ENV_FILE" ] && grep -q "^${key}=" "$ENV_FILE"; then
      tmp="$(mktemp)"; sed "s|^${key}=.*|${key}=${val}|" "$ENV_FILE" > "$tmp" && mv "$tmp" "$ENV_FILE"
    else
      echo "${key}=${val}" >> "$ENV_FILE"
    fi
  done <<< "$ENV_BLOCK"
  ok "Wrote endpoints into $ENV_FILE (your ANTHROPIC_API_KEY and any secrets are untouched)."
fi

echo
echo "Next:"
echo "  1. Set ANTHROPIC_API_KEY in ${ENV_FILE}  (the four agents run on Claude)."
echo "  2. python scripts/setup_foundry_iq.py     # build the Foundry IQ knowledge base (verify SDK first — setup/CLAUDE.md §7)"
echo "  3. python scripts/run_example.py --thesis examples/thesis.txt --html out/report.html"
