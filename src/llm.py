"""llm.py — Claude client for the four agents (EPIC-02).

Key resolution: ANTHROPIC_API_KEY from .env (local dev) → else Key Vault via managed
identity (production, ADR-0010). Models from .env: CLAUDE_MODEL / CLAUDE_CIO_MODEL.
"""
from __future__ import annotations
import os, json, re

__all__ = ["chat", "json_chat", "MODEL", "CIO_MODEL"]


def _load_env(path: str = ".env") -> None:
    if os.path.exists(path):
        for line in open(path, encoding="utf-8"):
            s = line.strip()
            if s and not s.startswith("#") and "=" in s:
                k, v = s.split("=", 1)
                os.environ.setdefault(k.strip(), v.strip())


_load_env()
MODEL = os.environ.get("CLAUDE_MODEL", "claude-sonnet-4-6")
CIO_MODEL = os.environ.get("CLAUDE_CIO_MODEL", MODEL)
# anthropic (Anthropic API) | foundry (Claude deployed in Microsoft Foundry — Option B, ADR-0013)
BACKEND = os.environ.get("LLM_BACKEND", "anthropic").lower()
_client = None


def _key() -> str:
    # Canonical resolution lives in config.py (STORY-06.2.01): local-dev
    # ANTHROPIC_API_KEY → else Key Vault via managed identity (keyless).
    try:
        from .config import get_anthropic_key
    except ImportError:  # script-style import (no package context)
        from config import get_anthropic_key  # type: ignore
    return get_anthropic_key()


def _foundry_base() -> str:
    b = os.environ.get("FOUNDRY_ANTHROPIC_BASE_URL")
    if b:
        return b.rstrip("/")
    acct = os.environ.get("FOUNDRY_ACCOUNT")
    if not acct:
        raise RuntimeError("LLM_BACKEND=foundry needs FOUNDRY_ACCOUNT or FOUNDRY_ANTHROPIC_BASE_URL")
    return f"https://{acct}.services.ai.azure.com/anthropic"


def _get():
    global _client
    if _client is None:
        from anthropic import Anthropic
        if BACKEND == "foundry":
            # Claude-in-Foundry speaks the Anthropic Messages API at <resource>.services.ai.azure.com/anthropic.
            # `model` passed to messages.create is the Foundry *deployment* name (= CLAUDE_MODEL).
            base = _foundry_base()
            fkey = os.environ.get("FOUNDRY_ANTHROPIC_KEY", "").strip()
            if fkey:                                   # API-key auth
                _client = Anthropic(base_url=base, api_key=fkey)
            else:                                      # Entra ID auth (managed identity / az login)
                from azure.identity import DefaultAzureCredential
                tok = DefaultAzureCredential().get_token("https://ai.azure.com/.default").token
                _client = Anthropic(base_url=base, api_key="entra",
                                    default_headers={"Authorization": f"Bearer {tok}"})
        else:
            _client = Anthropic(api_key=_key())
    return _client


def chat(system: str, user: str, model: str | None = None, max_tokens: int = 4000) -> str:
    r = _get().messages.create(
        model=model or MODEL, max_tokens=max_tokens,
        system=system, messages=[{"role": "user", "content": user}],
    )
    return "".join(b.text for b in r.content if getattr(b, "type", "") == "text")


def json_chat(system: str, user: str, model: str | None = None, max_tokens: int = 4000):
    txt = chat(system + "\n\nReturn ONLY valid JSON — no prose, no markdown fences.", user, model, max_tokens)
    return _parse_json(txt)


def _parse_json(txt: str):
    txt = txt.strip()
    m = re.search(r"```(?:json)?\s*(.*?)```", txt, re.S)
    if m:
        txt = m.group(1).strip()
    try:
        return json.loads(txt)
    except Exception:
        starts = [i for i in (txt.find("{"), txt.find("[")) if i >= 0]
        i = min(starts) if starts else 0
        j = max(txt.rfind("}"), txt.rfind("]"))
        return json.loads(txt[i:j + 1])
