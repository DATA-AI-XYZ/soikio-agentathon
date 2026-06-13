"""extract.py — thesis → atomic testable claims (EPIC-02 FEAT-02.1). The pipeline's input contract."""
from __future__ import annotations
import os
import llm

_P = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SYSTEM = open(os.path.join(_P, "prompts", "system.md"), encoding="utf-8").read()
PROMPT = open(os.path.join(_P, "prompts", "extract.md"), encoding="utf-8").read()


def extract(thesis: str) -> dict:
    data = llm.json_chat(SYSTEM + "\n\n" + PROMPT, f"THESIS:\n{thesis}")
    claims = data.get("claims", []) if isinstance(data, dict) else []
    for i, c in enumerate(claims):
        c.setdefault("id", f"c{i + 1}")
        c.setdefault("horizon", "medium")
        c.setdefault("load_bearing", False)
        if not c.get("lenses"):
            c["lenses"] = ["fundamental"]
    return {"entity": (data or {}).get("entity"), "claims": claims}
