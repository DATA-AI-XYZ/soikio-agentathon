"""config.py — secret/config loader (STORY-06.2.01, ADR-0010).

The canonical place the app gets its Anthropic key and an Azure credential.

Key resolution (ADR-0010):
  1. local dev  — ANTHROPIC_API_KEY from .env (any real `sk-ant-…` value)
  2. production — Key Vault `anthropic-api-key` via the user-assigned managed
     identity (AZURE_CLIENT_ID), keyless `DefaultAzureCredential`.

Every Azure SDK client in this codebase authenticates with the credential
returned by `credential()` — no account keys or connection strings.
"""
from __future__ import annotations

import os
import time

__all__ = ["get_anthropic_key", "credential", "load_env"]

# A placeholder left in .env.example / unconfigured envs. Treated as "not set"
# so we fall through to Key Vault rather than handing back a fake key.
_PLACEHOLDER_PREFIX = "sk-ant-..."


def load_env(path: str = ".env") -> None:
    """Best-effort .env loader (local dev). No-op when the file is absent
    (the container has no .env — it reads real env vars + Key Vault)."""
    if os.path.exists(path):
        for line in open(path, encoding="utf-8"):
            s = line.strip()
            if s and not s.startswith("#") and "=" in s:
                k, v = s.split("=", 1)
                os.environ.setdefault(k.strip(), v.strip())


load_env()


def credential():
    """The one keyless credential for every Azure SDK client.

    Pins the user-assigned managed identity (AZURE_CLIENT_ID) so the
    Container App authenticates as the UAMI that holds the RBAC grants;
    locally it falls through DefaultAzureCredential's chain (az login)."""
    from azure.identity import DefaultAzureCredential

    client_id = os.environ.get("AZURE_CLIENT_ID", "").strip()
    if client_id:
        return DefaultAzureCredential(managed_identity_client_id=client_id)
    return DefaultAzureCredential()


def _local_key() -> str:
    k = os.environ.get("ANTHROPIC_API_KEY", "").strip()
    if k and not k.startswith(_PLACEHOLDER_PREFIX):
        return k
    return ""


def get_anthropic_key(retries: int = 3, backoff_s: float = 2.0) -> str:
    """Return the Anthropic key.

    Local dev short-circuits on ANTHROPIC_API_KEY. Otherwise fetches from
    Key Vault keyless, retrying a few times to ride out managed-identity /
    RBAC propagation lag on a cold container start (story risk note)."""
    local = _local_key()
    if local:
        return local

    vault_uri = os.environ["KEY_VAULT_URI"]
    secret_name = os.environ.get("ANTHROPIC_SECRET_NAME", "anthropic-api-key")

    from azure.keyvault.secrets import SecretClient

    last_err: Exception | None = None
    for attempt in range(retries):
        try:
            sc = SecretClient(vault_uri, credential())
            return sc.get_secret(secret_name).value
        except Exception as e:  # transient auth/RBAC lag on first start
            last_err = e
            if attempt < retries - 1:
                time.sleep(backoff_s * (attempt + 1))
    raise RuntimeError(
        f"Could not read secret '{secret_name}' from {vault_uri} keyless "
        f"after {retries} attempts: {last_err}"
    )
