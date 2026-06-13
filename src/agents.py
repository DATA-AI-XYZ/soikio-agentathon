"""agents.py — grounding gather + the three stance agents Bull / Bear / Caution (EPIC-02 FEAT-02.2).

Each stance makes ONE structured Claude call over the shared, cited evidence bundle —
reliable and cheap. Bull emits supporting points; Bear/Caution emit typed cracks.
"""
from __future__ import annotations
import os, json
from typing import Literal
from pydantic import BaseModel, ConfigDict, Field
import llm, foundry_iq, lenses

_P = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SYSTEM = open(os.path.join(_P, "prompts", "system.md"), encoding="utf-8").read()


# --- stance-output contract (STORY-02.2.02/03/04 / ADR-0017) ----------------------------
class StancePoint(BaseModel):
    """One stance point/crack. The asserted text is `point`; `claim_id` references the claim it
    concerns. `extra='allow'` keeps any model-added fields. Consumed by cio.build_conflict_map."""
    model_config = ConfigDict(extra="allow")
    claim_id: str
    point: str
    crack_type: Literal["contradicted", "unsupported", "vulnerable", "support"]
    citations: list[str] = Field(default_factory=list)
    lens: str | None = None
    agent_severity_hint: str | None = None
    confidence: float = 0.0
    stance: str


def validate_stance(points: list[dict]) -> list[StancePoint]:
    """Validate a stance's points against the schema (raises on contract violation)."""
    return [StancePoint.model_validate(p) for p in points]


def _prompt(name: str) -> str:
    return open(os.path.join(_P, "prompts", f"{name}.md"), encoding="utf-8").read()


def gather_grounding(extracted: dict, per_query: int = 3) -> list[dict]:
    """Query Foundry IQ per claim/lens; return de-duped sources with stable ids S1.., each cited by the agents."""
    ent = extracted.get("entity") or {}
    name = ent.get("name") or ent.get("ticker") or ""
    sources, seen = [], set()
    for claim in extracted["claims"]:
        for lens, q in lenses.queries_for(claim, name):
            r = foundry_iq.query(q)
            for e in r["extracts"][:per_query]:
                content = (e.get("content") or "").strip()
                key = content[:90].lower()
                if content and key not in seen:
                    seen.add(key)
                    sources.append({
                        "id": f"S{len(sources) + 1}", "lens": lens,
                        "claim_id": claim["id"], "content": content[:1500],
                    })
    return sources


def _bundle(sources: list[dict]) -> str:
    return "\n\n".join(f"[{s['id']}] (lens={s['lens']}, claim={s['claim_id']}) {s['content']}" for s in sources)


_SCHEMA = (
    'Return JSON: {"points":[{"claim_id":"c1","point":"one sentence","crack_type":'
    '"contradicted|unsupported|vulnerable|support","citations":["S1"],"lens":"risk",'
    '"agent_severity_hint":"high|medium|low","confidence":0.0}]}. '
    'Cite ONLY ids from the evidence (e.g. S1). For "unsupported" cracks, citations:[] is allowed. '
    'Bull points use crack_type "support".'
)


def run_stance(name: str, thesis: str, extracted: dict, sources: list[dict], extra: str = "") -> list[dict]:
    system = SYSTEM + "\n\n" + _prompt(name)
    user = (
        f"THESIS:\n{thesis}\n\nEXTRACTED CLAIMS:\n{json.dumps(extracted['claims'], indent=2)}\n\n"
        f"EVIDENCE (cite by id; NEVER cite an id not listed below):\n{_bundle(sources)}\n\n"
        f"{extra}\n\n{_SCHEMA}"
    )
    data = llm.json_chat(system, user, max_tokens=4000)
    pts = data.get("points", []) if isinstance(data, dict) else (data or [])
    for p in pts:
        p["stance"] = name
    return pts
