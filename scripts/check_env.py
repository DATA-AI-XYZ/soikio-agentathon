#!/usr/bin/env python
"""check_env.py — preflight verifier (STORY-00.3.02, ADR-0011).

Proves, before any feature code runs, that:
  1. every required config var is present (names the first missing one, exits non-zero);
  2. keyless `DefaultAzureCredential` resolves and can read the Key Vault secret + list the
     `public-docs` blob container — no account key / connection string;
  3. the Foundry IQ knowledge base answers a retrieve probe.

Exit 0 only when all selected checks pass. Mirrors the container's environment model: config
comes from the process env (a local `.env` is loaded for dev convenience, same as the app modules).

    python scripts/check_env.py                 # all checks
    python scripts/check_env.py --only kv,blob   # subset
"""
from __future__ import annotations

import argparse
import os
import sys
import time

# Make `src` importable when run as `python scripts/check_env.py` from the repo root.
_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _ROOT not in sys.path:
    sys.path.insert(0, _ROOT)

REQUIRED = [
    "KEY_VAULT_URI",
    "ANTHROPIC_SECRET_NAME",
    "AZURE_CLIENT_ID",
    "AZURE_SEARCH_ENDPOINT",
    "AZURE_SEARCH_KNOWLEDGE_BASE",
    "AZURE_STORAGE_ACCOUNT",
    "AZURE_STORAGE_CONTAINER",
]


def _load_env(path: str = ".env") -> None:
    """Dev convenience: load .env from cwd if present (same pattern as src/config.py).
    The container injects real env vars and has no .env — load is a no-op there."""
    if os.path.exists(path):
        for line in open(path, encoding="utf-8"):
            s = line.strip()
            if s and not s.startswith("#") and "=" in s:
                k, v = s.split("=", 1)
                os.environ.setdefault(k.strip(), v.strip())


def _fail(msg: str, code: int = 2) -> None:
    # ASCII-only output: a non-ASCII glyph crashes on the Windows cp1252 console
    # (cf. BUG-20260613-01 / the run_example.py UnicodeEncodeError fix).
    print(f"check_env: FAIL - {msg}", file=sys.stderr)
    sys.exit(code)


def _retry(fn, what: str, attempts: int = 3, backoff_s: float = 2.0):
    """Ride out managed-identity / RBAC propagation lag on a cold environment."""
    last = None
    for i in range(attempts):
        try:
            return fn()
        except Exception as e:  # noqa: BLE001 — surface the final cause on exhaustion
            last = e
            if i < attempts - 1:
                time.sleep(backoff_s * (i + 1))
    _fail(f"{what}: {last}")


def check_vars() -> None:
    for v in REQUIRED:
        if not os.environ.get(v, "").strip():
            _fail(f"missing required env var: {v}")
    print("vars: OK")


def check_kv() -> None:
    from azure.keyvault.secrets import SecretClient

    from src.config import credential

    name = os.environ.get("ANTHROPIC_SECRET_NAME", "anthropic-api-key")

    def _go():
        sc = SecretClient(os.environ["KEY_VAULT_URI"], credential())
        s = sc.get_secret(name)
        assert s.value, "secret has no value"
        return s

    _retry(_go, "kv")
    print(f"kv: OK (read secret '{name}' keyless)")


def check_blob() -> None:
    from azure.storage.blob import BlobServiceClient

    from src.config import credential

    acct = os.environ["AZURE_STORAGE_ACCOUNT"]
    container = os.environ["AZURE_STORAGE_CONTAINER"]

    def _go():
        bsc = BlobServiceClient(f"https://{acct}.blob.core.windows.net", credential())
        return sum(1 for _ in bsc.get_container_client(container).list_blobs())

    n = _retry(_go, "blob")
    print(f"blob: OK (listed '{container}' keyless - {n} blob(s))")


def check_kb() -> None:
    # Force the live backend — a preflight that silently passed on the mock would be a lie.
    os.environ.pop("FOUNDRY_IQ_MOCK", None)
    if os.environ.get("FOUNDRY_IQ_BACKEND", "").lower() == "mock":
        os.environ.pop("FOUNDRY_IQ_BACKEND")
    from src import foundry_iq

    def _go():
        r = foundry_iq.query("NVIDIA China export controls risk")
        if not r["extracts"]:
            raise RuntimeError("knowledge base retrieve returned 0 extracts")
        return r

    r = _retry(_go, "kb")
    print(f"kb: OK (retrieve returned {len(r['extracts'])} extracts)")


CHECKS = {"kv": check_kv, "blob": check_blob, "kb": check_kb}


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="Keyless env + connectivity preflight.")
    ap.add_argument(
        "--only",
        default="",
        help="comma-separated subset of: " + ",".join(CHECKS) + " (default: all)",
    )
    args = ap.parse_args(argv)

    _load_env()
    check_vars()  # always — the var gate names the first missing var and exits non-zero

    selected = (
        [c.strip() for c in args.only.split(",") if c.strip()]
        if args.only
        else list(CHECKS)
    )
    unknown = [c for c in selected if c not in CHECKS]
    if unknown:
        _fail(f"unknown --only check(s): {','.join(unknown)}")

    for c in selected:
        CHECKS[c]()

    print("check_env: ALL PASS")
    return 0


if __name__ == "__main__":
    sys.exit(main())
