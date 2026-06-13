"""foundry_iq.py — retrieval client over the live Foundry IQ knowledge base (EPIC-01 FEAT-01.3).

The single grounding interface the agents call. Cite-or-silence depends on this returning
real, source-linked extracts — never model memory.

    query(question)        -> {"extracts": [...], "citations": [...], "activity": [...]}
    coverage(claim, lens)  -> bool   (does any indexed doc cover this claim/lens?)

Set FOUNDRY_IQ_MOCK=1 to use a local fixture (offline, no Azure) — a keyword pass over the
HTML filings in knowledge/. Lets the agents/report be built and demoed without live retrieval.
"""
from __future__ import annotations
import os, json, glob, re

__all__ = ["query", "coverage"]


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
MOCK = os.environ.get("FOUNDRY_IQ_MOCK", "").lower() in ("1", "true", "yes")

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


def query(question: str, max_tokens: int = 4000) -> dict:
    """Return grounded extracts + citations for a question. Never fabricates."""
    if MOCK:
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
    return {
        "extracts": extracts,
        "citations": d.get("references", []) or [],
        "activity": d.get("activity", []) or [],
    }


def coverage(claim: str, lens: str | None = None) -> bool:
    """Does any indexed document cover this claim (optionally for a lens)?"""
    q = claim if not lens else f"{claim} ({lens})"
    return bool(query(q, max_tokens=1000)["extracts"])


# --- mock fixture (FOUNDRY_IQ_MOCK=1) — offline keyword retrieval over knowledge/*.htm ---
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
    scored.sort(reverse=True)
    extracts, citations = [], []
    for i, (_, src, para) in enumerate(scored[:8]):
        extracts.append({"ref_id": i, "content": para[:1200]})
        citations.append({"ref_id": i, "source": src, "locator": "mock"})
    return {"extracts": extracts, "citations": citations, "activity": [{"mock": True, "terms": terms}]}


if __name__ == "__main__":
    import sys
    r = query(sys.argv[1] if len(sys.argv) > 1 else "NVIDIA China export controls risk")
    print(f"extracts={len(r['extracts'])} citations={len(r['citations'])}")
    for e in r["extracts"][:2]:
        print(f"\n[ref {e.get('ref_id')}] {str(e.get('content',''))[:240]}...")
