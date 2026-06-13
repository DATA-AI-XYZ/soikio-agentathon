#!/usr/bin/env python3
"""Build the Foundry IQ knowledge base over the public filings in Blob (STORY-00.2.01).

Creates an Azure Blob knowledge source + a knowledge base on the live Azure AI Search
service, keyless via DefaultAzureCredential. Written against azure-search-documents 12.0.0
(the installed API surface, introspected — not guessed). Decisions: ADR-0011, ADR-0013.

Usage:
    python scripts/setup_foundry_iq.py            # create knowledge source + knowledge base
    python scripts/setup_foundry_iq.py --probe "What are NVIDIA's key risks?"
"""
from __future__ import annotations
import os, sys, json


def load_env(path: str = ".env") -> None:
    if not os.path.exists(path):
        return
    for line in open(path, encoding="utf-8"):
        line = line.strip()
        if line and not line.startswith("#") and "=" in line:
            k, v = line.split("=", 1)
            os.environ.setdefault(k.strip(), v.strip())


load_env()

SUB = os.environ["AZURE_SUBSCRIPTION_ID"]
RG = "REDACTED-resource-group"
SEARCH_ENDPOINT = os.environ["AZURE_SEARCH_ENDPOINT"]
KB_NAME = os.environ.get("AZURE_SEARCH_KNOWLEDGE_BASE", "REDACTED-kb")
KS_NAME = os.environ.get("AZURE_SEARCH_KNOWLEDGE_SOURCE", "REDACTED-docs")
STORAGE = os.environ.get("AZURE_STORAGE_ACCOUNT", "REDACTED-storage")
CONTAINER = os.environ.get("AZURE_STORAGE_CONTAINER", "public-docs")
OPENAI_ENDPOINT = os.environ["AZURE_OPENAI_ENDPOINT"].rstrip("/")
PLANNER = os.environ.get("AZURE_OPENAI_PLANNER_DEPLOYMENT", "gpt-4.1-mini")
EMBED = os.environ.get("AZURE_OPENAI_EMBEDDING_DEPLOYMENT", "text-embedding-3-large")

# Managed-identity connection string form (keyless): the storage resource ID.
BLOB_CONN = (
    f"ResourceId=/subscriptions/{SUB}/resourceGroups/{RG}"
    f"/providers/Microsoft.Storage/storageAccounts/{STORAGE};"
)


def _client():
    from azure.identity import DefaultAzureCredential
    from azure.search.documents.indexes import SearchIndexClient
    return SearchIndexClient(SEARCH_ENDPOINT, DefaultAzureCredential())


def build_knowledge_source():
    from azure.search.documents.indexes.models import (
        AzureBlobKnowledgeSource, AzureBlobKnowledgeSourceParameters,
    )
    return AzureBlobKnowledgeSource(
        name=KS_NAME,
        description="Public SEC filings (NVDA/MSFT/BP) — clean-room grounding corpus.",
        azure_blob_parameters=AzureBlobKnowledgeSourceParameters(
            connection_string=BLOB_CONN,
            container_name=CONTAINER,
        ),
    )


def build_knowledge_base():
    from azure.search.documents.indexes.models import (
        KnowledgeBase, KnowledgeSourceReference,
        KnowledgeBaseAzureOpenAIModel, AzureOpenAIVectorizerParameters,
    )
    planner = KnowledgeBaseAzureOpenAIModel(
        azure_open_ai_parameters=AzureOpenAIVectorizerParameters(
            resource_url=OPENAI_ENDPOINT,
            deployment_name=PLANNER,
            model_name="gpt-4.1-mini",
        )
    )
    return KnowledgeBase(
        name=KB_NAME,
        description="Foundry IQ knowledge base for the thesis red-team.",
        knowledge_sources=[KnowledgeSourceReference(name=KS_NAME)],
        models=[planner],
    )


def create():
    c = _client()
    print(f"→ creating knowledge source '{KS_NAME}' over {STORAGE}/{CONTAINER} ...")
    ks = c.create_or_update_knowledge_source(build_knowledge_source())
    print(f"  ✓ knowledge source: {ks.name}")
    print(f"→ creating knowledge base '{KB_NAME}' (planner={PLANNER}) ...")
    kb = c.create_or_update_knowledge_base(build_knowledge_base())
    print(f"  ✓ knowledge base: {kb.name}")
    print("Done. (Indexing runs async — give it a minute before probing.)")


def probe(query: str):
    from azure.identity import DefaultAzureCredential
    from azure.search.documents.knowledgebases import KnowledgeBaseRetrievalClient
    from azure.search.documents.knowledgebases.models import (
        KnowledgeBaseRetrievalRequest, KnowledgeRetrievalSemanticIntent, KnowledgeSourceParams,
    )
    client = KnowledgeBaseRetrievalClient(SEARCH_ENDPOINT, DefaultAzureCredential(), knowledge_base_name=KB_NAME)
    req = KnowledgeBaseRetrievalRequest(
        intents=[KnowledgeRetrievalSemanticIntent(search=query)],
        include_activity=True,
    )
    resp = client.retrieve(req)
    print(json.dumps(resp.as_dict() if hasattr(resp, "as_dict") else str(resp), indent=2, default=str)[:4000])


if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "--probe":
        probe(sys.argv[2] if len(sys.argv) > 2 else "What are the key risk factors?")
    else:
        create()
