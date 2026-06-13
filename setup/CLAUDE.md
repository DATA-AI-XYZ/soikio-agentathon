# Build & Setup Guide — soikio-agentathon

How to stand this project up and write its code. This file is the single entry point for the build; it also serves as guidance for an AI-assisted coding session. If you load it into a coding tool, consider copying it to the repo root as `CLAUDE.md` so it auto-loads.

> Deadline: **14 June 2026.** Scope is deliberately small — one ticker, four agents, a handful of public docs. Resist scope creep.

---

## 1. What we're building

**Red-team your investment thesis.** The user submits a thesis; three stance agents — **Bull** (steelman), **Bear** (attack), **Caution** (what breaks it) — test it across six lenses against public documents grounded by **Foundry IQ**; a **CIO** builds the **Kintsugi conflict map** and rates robustness, rendered as an interactive HTML report. Governing philosophy: the **Kintsugi Principle** (`../docs/kintsugi-principle.md`).

Canonical design docs (read before coding):
- Architecture — [`../docs/architecture.md`](../docs/architecture.md)
- Output contract — [`../docs/output-schema.md`](../docs/output-schema.md)
- Report — [`../docs/report-spec.md`](../docs/report-spec.md)
- Prompts — [`../prompts/`](../prompts/)
- Decisions — [`../docs/adr/`](../docs/adr/)

---

## 2. Non-negotiable invariants (the build "constitution")

Every file must respect these. They are the point of the project.

1. **Never invent numbers.** Every figure traces to a retrieved source. No source → drop or flag, never fabricate. (cite-or-silence)
2. **Analysis, not advice.** Headline verdict is **thesis robustness — Holds / Contested / Breaks**; equity lean (Bullish/Caution/Bearish) is secondary. **BUY / SELL / HOLD are forbidden** in any output — `citations.py` enforces this.
3. **Conflict is signal.** Surface disagreement; don't average it away.
4. **Clean-room.** Public data only. No proprietary prompts, mappings, thresholds, or private data — ever. All prompts are the fresh ones in `../prompts/`.
5. **Deterministic presentation.** The HTML report is rendered by a template (`render.py`), never an LLM (ADR-0005).
6. **Honest gaps.** A lens with no evidence is reported as "thin", not hidden — it lowers `data_completeness`.

---

## 3. Prerequisites

- **Anthropic API key** for Claude (the agents) — or Claude deployed in Microsoft Foundry.
- Azure subscription with Microsoft Foundry (New Foundry) + a **small** Azure OpenAI model (e.g. `gpt-4o-mini`) for the Foundry IQ planner. **No large `gpt-4o` quota needed.**
- Python 3.11+, `az` CLI (`az login`).
- `pip install -r ../requirements.txt` (pin versions first).

## 4. Azure resources to provision

(Full steps in [`../docs/runbook.md`](../docs/runbook.md).)

| Resource | Purpose |
|----------|---------|
| Microsoft Foundry project (Agent Service) | hosts the four agents |
| Azure AI Search (agentic-retrieval capable; free tier ok) | indexing + retrieval under Foundry IQ |
| Foundry IQ knowledge base + Blob knowledge source | grounding over public docs |
| Claude (Anthropic key, or in-Foundry) | the four agents' reasoning |
| Azure OpenAI deployment (small, e.g. `gpt-4o-mini`) | Foundry IQ query planner only |
| Azure Storage account + Blob container | the public documents |

**RBAC** (managed identity, least privilege): *Search Index Data Reader* (+ Contributor during setup) on Search; *Storage Blob Data Reader* on the container; *Cognitive Services OpenAI User* on the OpenAI deployment.

## 5. Config

```bash
cp ../.env.example ../.env     # fill endpoints; NO secrets — use managed identity
```

## 6. Public documents

Upload 2–4 public files (e.g. a 10-K, a macro release) to the Blob container. Record each in [`../knowledge/README.md`](../knowledge/README.md) with source URL + date. Keep it small.

---

## 7. ⚠️ Verify the Foundry IQ API FIRST

The exact Foundry IQ / Azure AI Search SDK calls (create knowledge base, add knowledge source, query agentic retrieval) are new (June 2026) and **must be confirmed against Microsoft Learn before writing `foundry_iq.py` and `setup_foundry_iq.py`** — do not guess them.

- What is Foundry IQ — https://learn.microsoft.com/en-us/azure/foundry/agents/concepts/what-is-foundry-iq
- Connect Foundry IQ to Agent Service — https://learn.microsoft.com/en-us/azure/foundry/agents/how-to/foundry-iq-connect
- Create a knowledge base — https://learn.microsoft.com/en-us/azure/search/agentic-retrieval-how-to-create-knowledge-base
- Agentic retrieval overview — https://learn.microsoft.com/en-us/azure/search/agentic-retrieval-overview

---

## 8. Build plan — file by file

Write these in `../src/` and `../scripts/`. Each conforms to the schema in `output-schema.md`.

| File | Responsibility | Key behaviour |
|------|----------------|---------------|
| `src/extract.py` | Thesis → testable claims. | Runs `prompts/extract.md`: 3–6 atomic claims, each with `load_bearing` + `lenses`. The pipeline's input contract. |
| `src/foundry_iq.py` | Foundry IQ client. | `query(question) -> {extracts[], citations[]}` (grounded extracts + citation objects: source_id, locator, quote) **and** `coverage(claim, lens) -> bool` (does any doc cover this?). Verify SDK first (§7). |
| `src/lenses.py` | The six lenses + per-lens question templates. | `LENSES = [...]`; helper to build a stance's per-lens queries. Generic only — see `../prompts/lenses.md`. |
| `src/bull.py` / `bear.py` / `caution.py` | One stance each (**Claude**). | Load its prompt (`../prompts/*.md`) + `system.md`, call Claude, run the six lenses via `foundry_iq`, emit the stance object (points with lens/citations/confidence, assumptions, stance_confidence). |
| `src/cio.py` | Adjudicator (**Claude + deterministic scorer**). | Build the **Kintsugi `conflict_map`**; compute severity, `thesis_robustness` (Holds/Contested/Breaks) and confidence **deterministically** per `docs/scoring.md`. Build `domain_findings` pivot. |
| `src/citations.py` | The guard (**faithfulness, not just presence**). | Per `docs/reliability-spec.md`: quote-contains-figure + quote-in-extract checks (reject fabricated citations); coverage gate (`unsupported` vs `data_gap`); precise BUY/SELL/HOLD intent block. |
| `src/render.py` | Deterministic HTML report. | JSON brief → self-contained HTML matching `report-spec.md` (mirror `report.sample.html`). No LLM. Mockup banner only if `entity.sample`. |
| `src/agent.py` | Orchestration entry. | ticker → run 3 stances (parallel ok) → CIO → validate (pydantic) → return brief; capture `run` telemetry (latency, retrievals, status per agent). |
| `scripts/setup_foundry_iq.py` | Build the knowledge base. | Create KB + Blob knowledge source, index docs, set retrieval effort. Verify SDK first (§7). |
| `scripts/run_example.py` | One-command demo. | `--thesis examples/thesis.txt [--html out/report.html]`; runs `agent.py`, prints/saves brief + renders report. |

Validate all outputs against `output-schema.md` with `pydantic`. Keep models swappable via `.env`.

## 9. Run sequence

```bash
python scripts/setup_foundry_iq.py                          # once: build the knowledge base
python scripts/run_example.py --thesis examples/thesis.txt --html out/report.html
```

## 10. Def