"""foundry_iq.py — retrieval client over the live Foundry IQ knowledge base (EPIC-01 FEAT-01.3).

The single grounding interface the agents call. Cite-or-silence depends on this returning
real, source-linked extracts — never model memory.

    query(question)        -> {"extracts": [...], "citations": [Citation...], "activity": [...]}
    coverage(claim, lens)  -> bool   (does any indexed doc cover this claim/lens?)

The return shape is validated against the documented citation contract (Pydantic models below,
ADR-0015): every citation carries `source_id`, `quote`, `locator` (doc-level fallback).

Backend selection (ADR-0015): the offline mock fixture is used when EITHER `FOUNDRY_IQ_MOCK=1`
OR `FOUNDRY_IQ_BACKEND=mock` is set — a keyword pass over the HTML filings in knowledge/, with
zero Azure calls. Lets the agents/report be built, tested, and demoed without live retrieval.
"""
from __future__ import annotations
import os, json, glob, re, hashlib
from pydantic import BaseModel, ConfigDict, Field

__all__ = ["query", "coverage", "Citation", "Extract", "QueryResult",
           "is_fresh", "current_corpus_version"]


# --- citation contract (STORY-01.3.01 / ADR-0015) ---------------------------------------
class Citation(BaseModel):
    """One source-linked citation. `locator` falls back to doc-level when no page/section exists."""
    source_id: str
    quote: str
    locator: str = "doc-level"


class Extract(BaseModel):
    """A retrieved evidence span. `extra='allow'` preserves any live-payload fields downstream reads."""
    model_config = ConfigDict(extra="allow")
    ref_id: int | None = None
    content: str


class QueryResult(BaseModel):
    extracts: list[Extract] = Field(default_factory=list)
    citations: list[Citation] = Field(default_factory=list)
    activity: list = Field(default_factory=list)
    corpus_version: str = ""  # ADR-0022 freshness stamp: recalled evidence carrying a stale version is never served as fresh


def _load_env(path: str = ".env") -> None:
    if os.path.exists(path):
        for line in open(path, encoding="utf-8"):
            line = line.strip()
            if line and not line.startswith("#") and "=" in line:
                k, v = line.split("=", 1)
                os.environ.setdefault(k.strip(), v.strip())


_load_env()
SEARCH_ENDPOINT = os.environ.get("AZURE_SEARCH_ENDPOINT", "")
KB_NAME = os.environ.get("AZURE_SEARCH_KNOWLEDGE_BASE", "REDACTED-kb")


def _use_mock() -> bool:
    """Offline mock backend if FOUNDRY_IQ_MOCK is truthy OR FOUNDRY_IQ_BACKEND=mock (ADR-0015).

    Read at call time so tests can select the backend by env with no caller change."""
    return (os.environ.get("FOUNDRY_IQ_MOCK", "").lower() in ("1", "true", "yes")
            or os.environ.get("FOUNDRY_IQ_BACKEND", "").lower() == "mock")


_client = None


def _get_client():
    global _client
    if _client is None:
        from azure.identity import DefaultAzureCredential
        from azure.search.documents.knowledgebases import KnowledgeBaseRetrievalClient
        _client = KnowledgeBaseRetrievalClient(
            SEARCH_ENDPOINT, DefaultAzureCredential(), knowledge_base_name=KB_NAME
        )
    return _client


# --- freshness rule (ADR-0022 / STORY-07.1.01) ------------------------------------------
# TTL backstop for recalled/cached evidence; configurable, forced > 0 so fresh results are
# never over-rejected. The rule lives in code with no external cache dependency.
DEFAULT_TTL_S = max(1, int(os.environ.get("FOUNDRY_IQ_TTL_S", "3600")))


def current_corpus_version() -> str:
    """A stable signal for the *current* corpus generation (ADR-0022).

    The version changes when the underlying corpus is re-indexed, so any cached/recalled entry
    stamped with an older version is invalidated. Std-lib only; no external cache dependency.

    - mock backend: a hash over knowledge/*.htm (name + size + mtime) — changes on re-index.
    - live backend: the knowledge-base identity is the backstop signal; absent a finer Foundry IQ
      version the versions match and the TTL is the freshness backstop (per ADR-0022).
    """
    if _use_mock():
        sig = []
        for path in sorted(glob.glob("knowledge/*.htm")):
            try:
                st = os.stat(path)
                sig.append(f"{os.path.basename(path)}:{st.st_size}:{st.st_mtime_ns}")
            except OSError:
                sig.append(os.path.basename(path))
        return "mock-" + hashlib.sha1("|".join(sig).encode("utf-8")).hexdigest()[:8]
    # TODO(STORY-07.2.x): swap for the Foundry IQ index-generation id once exposed. Until then the
    # live version is constant, so the TTL (not version-mismatch) is the freshness backstop (ADR-0022).
    return f"kb-{KB_NAME}"


def is_fresh(entry_version: str, current_version: str, age_s: float, ttl_s: float = DEFAULT_TTL_S) -> bool:
    """Pure freshness predicate (ADR-0022): True ONLY when the entry's corpus_version matches the
    current corpus_version AND its age is within the TTL.

    A version mismatch (corpus re-indexed) OR an age at/over the TTL → False, so recalled/cached
    evidence is never served as fresh. No external cache dependency — the rule lives in code.
    The TTL boundary is exclusive (age == ttl_s is expired); a non-positive age or TTL is never
    fresh, the conservative default.
    """
    if entry_version != current_version:
        return False
    return 0 <= age_s < ttl_s


def _validated(extracts: list, citations: list, activity: list) -> dict:
    """Build + validate the result against the contract, returning a plain dict (back-compat).

    Stamps the current corpus_version (ADR-0022) onto the result so any later recall/cache of this
    evidence can be freshness-checked via `is_fresh`."""
    return QueryResult(extracts=extracts, citations=citations, activity=activity,
                       corpus_version=current_corpus_version()).model_dump()


def _to_citation(raw: dict) -> dict:
    """Best-effort map a live reference dict to the {source_id, quote, locator} contract."""
    g = raw.get if isinstance(raw, dict) else (lambda *_: None)
    return {
        "source_id": str(g("source_id") or g("id") or g("doc_key") or g("ref_id")
                         or g("source") or g("title") or "unknown"),
        "quote": str(g("quote") or g("content") or g("text") or g("snippet") or ""),
        "locator": str(g("locator") or g("page") or g("section") or "doc-level"),
    }


def query(question: str, max_tokens: int = 4000) -> dict:
    """Return grounded extracts + contract-valid citations for a question. Never fabricates."""
    if _use_mock():
        return _mock_query(question)
    from azure.search.documents.knowledgebases.models import (
        KnowledgeBaseRetrievalRequest, KnowledgeRetrievalSemanticIntent,
    )
    # max_output_size_in_tokens must be >5000 if set; omit to use the service default.
    req = KnowledgeBaseRetrievalRequest(
        intents=[KnowledgeRetrievalSemanticIntent(search=question)],
        include_activity=True,
    )
    resp = _get_client().retrieve(req)
    d = resp.as_dict() if hasattr(resp, "as_dict") else dict(resp)
    extracts = []
    for msg in d.get("response", []) or []:
        for c in msg.get("content", []) or []:
            if c.get("type") == "text":
                try:
                    extracts.extend(json.loads(c["text"]))
                except Exception:
                    extracts.append({"ref_id": None, "content": c.get("text", "")})
    citations = [_to_citation(r) for r in (d.get("references", []) or [])]
    return _validated(extracts, citations, d.get("activity", []) or [])


def coverage(claim: str, lens: str | None = None) -> bool:
    """Does any indexed document cover this claim (optionally for a lens)?

    Threshold (ADR-0015): covered iff ≥1 covering extract is retrieved. Returns a plain `bool`
    directly consumable by the coverage gate (FEAT-03.2). Signature is FROZEN — the gate depends
    on `coverage(claim, lens)`."""
    q = claim if not lens else f"{claim} ({lens})"
    return bool(query(q, max_tokens=1000)["extracts"])


# --- mock fixture — offline keyword retrieval over knowledge/*.htm (zero Azure) ----------
_TAG = re.compile(r"<[^>]+>")
_WS = re.compile(r"\s+")
_mock_paras: list[tuple[str, str]] | None = None


def _mock_corpus() -> list[tuple[str, str]]:
    global _mock_paras
    if _mock_paras is None:
        _mock_paras = []
        for path in glob.glob("knowledge/*.htm"):
            src = os.path.basename(path)
            text = _WS.sub(" ", _TAG.sub(" ", open(path, encoding="utf-8", errors="ignore").read()))
            for para in re.split(r"(?<=[.!?])\s+(?=[A-Z])", text):
                if len(para) > 200:
                    _mock_paras.append((src, para.strip()))
    return _mock_paras


def _mock_query(question: str) -> dict:
    terms = [t for t in re.findall(r"[a-zA-Z]{4,}", question.lower())]
    scored = []
    for src, para in _mock_corpus():
        low = para.lower()
        score = sum(low.count(t) for t in terms)
        if score:
            scored.append((score, src, para))
    scored.sort(key=lambda t: t[0], reverse=True)
    extracts, citations = [], []
    for i, (_, src, para) in enumerate(scored[:8]):
        extracts.append({"ref_id": i, "content": para[:1200]})
        citations.append({"source_id": src, "quote": para[:240], "locator": "doc-level"})
    return _validated(extracts, citations, [{"mock": True, "terms": terms}])


if __name__ == "__main__":
    import sys
    r = query(sys.argv[1] if len(sys.argv) > 1 else "NVIDIA China export controls risk")
    print(f"extracts={len(r['extracts'])} citations={len(r['citations'])}")
    for e in r["extracts"][:2]:
        print(f"\n[ref {e.get('ref_id')}] {str(e.get('content',''))[:240]}...")
