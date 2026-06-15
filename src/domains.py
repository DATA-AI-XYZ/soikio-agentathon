"""
domains.py — the six domain-specialist agents.

Run BEFORE the debate. Each domain agent retrieves grounded evidence for its lens
(via Foundry IQ) about the user's claims and returns a per-domain finding. The output
is the `domain_findings` array (docs/output-schema.md); Bull/Bear/Caution argue over it.

Topology:  extract claims → domains.run_all() → {bull,bear,caution} → cio
Keeps the per-lens evidence trail clean and gives the debate real specialist depth.
"""
from __future__ import annotations
from typing import Callable, Optional
import pathlib, re

# Canonical six-lens taxonomy (ADR-0016) — matches src/lenses.py exactly:
# the legacy quant lens is now `technical`; the legacy event lens is now `valuation`.
LENSES = ["macro", "fundamental", "technical", "risk", "valuation", "supply_chain"]

# map lens id -> heading used in prompts/domains.md
_HEADINGS = {
    "macro": "Macro", "fundamental": "Fundamental", "technical": "Technical",
    "risk": "Risk", "valuation": "Valuation", "supply_chain": "Supply-chain",
}


def load_domain_prompt(lens: str, prompts_dir: str = "prompts") -> str:
    """Return system.md + the lens section from prompts/domains.md."""
    base = pathlib.Path(prompts_dir)
    system = (base / "system.md").read_text(encoding="utf-8")
    doc = (base / "domains.md").read_text(encoding="utf-8")
    heading = _HEADINGS[lens]
    # grab from '## <heading>' to the next '## ' or '---'
    m = re.search(rf"^##\s+{re.escape(heading)}\s*$(.*?)(?=^##\s|^---\s*$)", doc, re.S | re.M)
    section = m.group(1).strip() if m else ""
    return f"{system}\n\n# Domain: {heading}\n{section}"


def run_domain(
    lens: str,
    claims: list[dict],
    foundry_iq,                      # src.foundry_iq client: .query(q) -> {extracts,citations}, .coverage(claim,lens)->bool
    ask_claude: Callable[[str, str], str],   # (system_prompt, user_prompt) -> JSON string
    prompts_dir: str = "prompts",
) -> dict:
    """Run one domain specialist. Returns a domain_findings entry (see output-schema)."""
    # coverage probe first — distinguishes a real gap from a retrieval miss
    covered = any(foundry_iq.coverage(c["claim"], lens) for c in claims if lens in c.get("lenses", LENSES))
    if not covered:
        return {"lens": lens, "net_lean": "thin", "finding": "No covering document for this lens.",
                "points": [], "coverage": False}

    # gather grounded evidence per relevant claim
    evidence = []
    for c in claims:
        if lens in c.get("lenses", LENSES):
            r = foundry_iq.query(f"[{lens}] evidence bearing on: {c['claim']}")
            evidence.append({"claim_id": c["id"], "claim": c["claim"], "extracts": r["extracts"], "citations": r["citations"]})

    system = load_domain_prompt(lens, prompts_dir)
    user = (
        f"Entity claims and retrieved evidence for the **{lens}** lens:\n"
        f"{evidence}\n\nReturn the domain_findings JSON for this lens per the schema. "
        f"Only cite quotes present in the retrieved extracts."
    )
    raw = ask_claude(system, user)
    import json
    try:
        out = json.loads(raw)
    except Exception:
        out = {"lens": lens, "net_lean": "mixed", "finding": raw[:200], "points": [], "coverage": True}
    out["lens"] = lens
    out["coverage"] = True
    return out


def run_all(claims: list[dict], foundry_iq, ask_claude, prompts_dir: str = "prompts") -> list[dict]:
    """Run all six domain specialists concurrently. Returns the domain_findings array in LENS order.

    Each lens is independent (its own retrieval + one Claude call), so they run on a thread pool;
    a per-lens failure is isolated to a `coverage:false` row rather than voiding the panel."""
    from concurrent.futures import ThreadPoolExecutor

    # Warm the lazy singleton clients ONCE before the pool, so the six worker threads don't race to
    # build the (not necessarily thread-safe) Anthropic / Foundry IQ clients on first use.
    try:
        if not foundry_iq._use_mock():
            foundry_iq._get_client()
    except Exception:
        pass
    try:
        import llm
        llm._get()
    except Exception:
        pass

    def _one(lens: str) -> dict:
        try:
            return run_domain(lens, claims, foundry_iq, ask_claude, prompts_dir)
        except Exception as e:                       # isolate: one lens failing is a data gap, not a crash
            return {"lens": lens, "net_lean": "thin", "finding": f"domain error: {type(e).__name__}",
                    "points": [], "coverage": False}

    with ThreadPoolExecutor(max_workers=6) as ex:
        return list(ex.map(_one, LENSES))            # ex.map preserves LENSES order
