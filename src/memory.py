"""
memory.py — persistence / "memory" for the thesis red-team.

Stores every run's brief (thesis + conflict map + citations) so the product can:
  • recall past analyses (history / audit trail), and
  • reflect on the prior run for an entity (the resolution-loop / "what changed" seed).

Two backends, chosen by env (POC works with zero cloud):
  • LocalJsonStore  — writes ./runs/<run_id>.json + an index.jsonl   (default, offline)
  • BlobStore       — Azure Blob container (set MEMORY_BACKEND=blob)  (production)

Production target is the immutable audit trail (Cosmos/PostgreSQL);
this module is the seam that those swap in behind `MemoryStore`.
"""
from __future__ import annotations
import os, json, datetime, pathlib
from typing import Optional


def _now() -> str:
    return datetime.datetime.now(datetime.timezone.utc).isoformat()


# --- shape-tolerant derivations: work for both the real agent.run brief
#     (entity.ticker, run.id) and the simple {id,ticker,verdict} test shape ---
def _derive_id(brief: dict) -> str:
    run = brief.get("run") or {}
    return (brief.get("id") or run.get("run_id") or run.get("id")
            or f"sk-{datetime.datetime.now(datetime.timezone.utc):%Y%m%d-%H%M%S-%f}")


def _derive_ticker(brief: dict):
    e = brief.get("entity")
    if isinstance(e, dict):
        return e.get("ticker") or e.get("name")
    return brief.get("ticker")


def _index_row(brief: dict) -> dict:
    return {
        "id": brief.get("id") or _derive_id(brief),   # tolerate a legacy row missing 'id'
        "stored_at": brief.get("_stored_at"),
        "ticker": _derive_ticker(brief),
        "thesis_robustness": brief.get("thesis_robustness") or brief.get("verdict"),
        "confidence": brief.get("confidence"),
    }


class MemoryStore:
    """Interface. Implementations must be append-only (audit-grade): never mutate a saved brief."""
    def save_brief(self, brief: dict) -> str: ...
    def get_run(self, run_id: str) -> Optional[dict]: ...
    def list_runs(self, ticker: Optional[str] = None, limit: int = 50) -> list[dict]: ...
    def prior_run(self, ticker: str) -> Optional[dict]: ...


class LocalJsonStore(MemoryStore):
    """Offline default — one JSON file per run + an append-only index line."""
    def __init__(self, root: str = "runs"):
        self.root = pathlib.Path(root)
        self.root.mkdir(parents=True, exist_ok=True)
        self.index = self.root / "index.jsonl"

    def save_brief(self, brief: dict) -> str:
        run_id = _derive_id(brief)
        brief["id"] = run_id
        brief["_stored_at"] = _now()
        path = self.root / f"{run_id}.json"
        if not path.exists():            # append-only: never silently replace a saved run
            path.write_text(json.dumps(brief, indent=2), encoding="utf-8")
            with self.index.open("a", encoding="utf-8") as f:
                f.write(json.dumps(_index_row(brief)) + "\n")
        return run_id

    def _read_index(self) -> list[dict]:
        if not self.index.exists():
            return []
        return [json.loads(l) for l in self.index.read_text(encoding="utf-8").splitlines() if l.strip()]

    def get_run(self, run_id: str) -> Optional[dict]:
        p = self.root / f"{run_id}.json"
        return json.loads(p.read_text(encoding="utf-8")) if p.exists() else None

    def list_runs(self, ticker: Optional[str] = None, limit: int = 50) -> list[dict]:
        rows = self._read_index()
        if ticker:
            rows = [r for r in rows if (r.get("ticker") or "").upper() == ticker.upper()]
        return list(reversed(rows))[:limit]

    def prior_run(self, ticker: str) -> Optional[dict]:
        rows = self.list_runs(ticker=ticker, limit=1)
        return self.get_run(rows[0]["id"]) if rows and rows[0].get("id") else None


class BlobStore(MemoryStore):
    """Production — Azure Blob. Lazy-imports azure-storage-blob so the POC never needs it."""
    def __init__(self, container: Optional[str] = None):
        from azure.storage.blob import ContainerClient  # lazy
        from azure.identity import DefaultAzureCredential
        acct = os.environ["AZURE_STORAGE_ACCOUNT"]
        self.container = container or os.environ.get("MEMORY_CONTAINER", "runs")
        self.cc = ContainerClient(
            account_url=f"https://{acct}.blob.core.windows.net",
            container_name=self.container,
            credential=DefaultAzureCredential(),
        )

    def save_brief(self, brief: dict) -> str:
        run_id = _derive_id(brief)
        brief["id"] = run_id
        brief["_stored_at"] = _now()
        # append-only: overwrite=False so a run_id is never silently replaced (audit integrity)
        self.cc.upload_blob(f"{run_id}.json", json.dumps(brief, indent=2), overwrite=False)
        return run_id

    def get_run(self, run_id: str) -> Optional[dict]:
        try:
            return json.loads(self.cc.download_blob(f"{run_id}.json").readall())
        except Exception:
            return None

    def list_runs(self, ticker: Optional[str] = None, limit: int = 50) -> list[dict]:
        out = []
        for b in self.cc.list_blobs():
            d = self.get_run(b.name.removesuffix(".json")) or {}
            t = _derive_ticker(d)
            if ticker and (t or "").upper() != ticker.upper():
                continue
            out.append(_index_row(d))
        out.sort(key=lambda r: r.get("stored_at") or "", reverse=True)
        return out[:limit]

    def prior_run(self, ticker: str) -> Optional[dict]:
        rows = self.list_runs(ticker=ticker, limit=1)
        return self.get_run(rows[0]["id"]) if rows and rows[0].get("id") else None


def get_store() -> MemoryStore:
    return BlobStore() if os.environ.get("MEMORY_BACKEND") == "blob" else LocalJsonStore()


if __name__ == "__main__":  # tiny smoke test (offline)
    s = LocalJsonStore(root="runs")
    rid = s.save_brief({"thesis": {"entity": {"ticker": "MSFT"}}, "thesis_robustness": "Contested", "confidence": 0.62, "run": {}})
    print("saved", rid, "| prior:", (s.prior_run("MSFT") or {}).get("thesis_robustness"), "| runs:", len(s.list_runs()))
