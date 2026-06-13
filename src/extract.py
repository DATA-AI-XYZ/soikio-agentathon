"""extract.py — thesis → atomic testable claims (EPIC-02 FEAT-02.1). The pipeline's input contract.

Claims are validated against a Pydantic schema (ADR-0015 pattern) so the stance agents always
receive well-formed targets. Extraction never fabricates: it normalises defaults on what Claude
emits, but adds no claims of its own."""
from __future__ import annotations
import os
from pydantic import BaseModel, ConfigDict, Field
import llm

_P = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SYSTEM = open(os.path.join(_P, "prompts", "system.md"), encoding="utf-8").read()
PROMPT = open(os.path.join(_P, "prompts", "extract.md"), encoding="utf-8").read()

__all__ = ["extract", "Claim", "Extraction"]


class Claim(BaseModel):
    """One atomic, testable claim. `extra='allow'` keeps any model-added fields (e.g. rationale)."""
    model_config = ConfigDict(extra="allow")
    id: str
    claim: str
    load_bearing: bool = False
    lenses: list[str] = Field(default_factory=lambda: ["fundamental"])
    horizon: str = "medium"


class Extraction(BaseModel):
    model_config = ConfigDict(extra="allow")
    entity: dict | None = None
    claims: list[Claim] = Field(default_factory=list)


def extract(thesis: str) -> dict:
    data = llm.json_chat(SYSTEM + "\n\n" + PROMPT, f"THESIS:\n{thesis}")
    claims = data.get("claims", []) if isinstance(data, dict) else []
    for i, c in enumerate(claims):
        c.setdefault("id", f"c{i + 1}")
        c.setdefault("horizon", "medium")
        c.setdefault("load_bearing", False)
        if not c.get("lenses"):
            c["lenses"] = ["fundamental"]
    out = {"entity": (data or {}).get("entity"), "claims": claims}
    return Extraction.model_validate(out).model_dump()
