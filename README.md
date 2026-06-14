# soikio-agentathon

**Red-team your investment thesis.** You bring a thesis on a public equity; **Bull** steelmans it, **Bear** and **Caution** attack it across six analytical lenses — tested against public filings via **Microsoft Foundry IQ** — and a **CIO** returns a *Kintsugi conflict map*: every crack in your thesis, gilded and ranked, plus a robustness verdict.

> **Agents League @ AISF 2026** · Track: *Reasoning Agents (Microsoft Foundry)* · Microsoft IQ layer: *Foundry IQ*.

---

## Concept — why it's different

**The concept in one line:** an AI analyst that *refuses to fabricate* — it red-teams an investment thesis against the public record and shows its disagreements as the product, never as advice.

Most analysis agents assert. This one **red-teams a position you already hold** — and refuses to invent numbers:

- **You bring the thesis; the agents try to break it.** Bull steelmans it, Bear and Caution attack it against the public record. Confident-answer tools don't stress-test a view you already have.
- **The Kintsugi Principle — gild the cracks.** Disagreement is signal, not error. The headline output is a *conflict map*: every crack in your thesis, ranked by severity (⚡), each cited and paired with what would resolve it. See [`docs/kintsugi-principle.md`](docs/kintsugi-principle.md).
- **Cite-or-silence.** Every figure traces to a retrieved source. No source → dropped or flagged, never fabricated.
- **Analysis, not advice.** A robustness verdict — *Holds / Contested / Breaks* — with confidence. Never BUY/SELL/HOLD.

The method and the Kintsugi Principle are carried over from an internal multi-agent research system; this repository is a **clean-room** re-expression using public data only.

## How it works

```
Your investment thesis  ──►  tested against  ──►  Foundry IQ (public docs, cited)
        │
   ┌─────────────── RED-TEAM ───────────────┐
   │  Bull          Bear          Caution   │  steelman · attack · what breaks it
   │  (each across six analytical lenses)   │
   └────────────────┬───────────────────────┘
                    │
   CIO ── Kintsugi conflict map: cracks ranked by severity (⚡)
                    │
   Robustness verdict — Holds / Contested / Breaks
```

The six lenses each stance applies: **Macro · Fundamental · Technical · Risk · Valuation · Supply-chain** (the canonical taxonomy, ADR-0016).

Full diagram: [`docs/architecture.svg`](docs/architecture.svg). Design rationale: [`docs/architecture.md`](docs/architecture.md). Azure resources: [`docs/azure-architecture.svg`](docs/azure-architecture.svg).

## Architecture on Azure

| Resource | Role |
|----------|------|
| Microsoft Foundry — Agent Service | hosts the four agents |
| Foundry IQ knowledge base | shared grounding for all stances |
| Azure AI Search | indexing + agentic retrieval under Foundry IQ |
| Azure Blob Storage | public documents (the knowledge source) |
| Claude (Anthropic) | the four agents' reasoning |
| Azure OpenAI (small) | Foundry IQ retrieval query planning only |
| Microsoft Entra ID + managed identity | permission-aware access |

## Roadmap — experimental, not yet wired

> **These components are drafted on disk but standalone / experimental.** The shipped pipeline today is `extract → Bull/Bear/Caution → CIO → verdict`; `agent.run` does **not** call any of the items below yet. They are tracked as the next wave (OKR-2026-Q3) and each ships behind its own story + tests before it earns a "live" claim — this README will not describe them as running until then.

- **Auto-deployed frontend** — `web/` + `.github/workflows/deploy-pages.yml` (drafted; one-time GitHub Pages enablement still pending).
- **Memory / persistence** — `src/memory.py` (standalone module — append-only local-JSON / Azure Blob store; not yet called by the run path).
- **Domain agents** — six per-lens specialists (`src/domains.py`, `prompts/domains.md`), experimental; not yet integrated ahead of the debate. Intended lenses follow the canonical taxonomy (ADR-0016).
- **History & dashboard** — `web/history.html` (renders illustrative sample data; store-backed listing pending the persistence + API stories).
- **Reviewer agent** — `src/reviewer.py` (standalone retrospective; not yet integrated after the CIO). Deltas are computed in code, not by the model; predictive calibration stays `tracking` until outcome data exists.

See [`docs/upgrades.md`](docs/upgrades.md).

## Web frontend

A self-contained demo UI — submit → run → cited conflict map, in the SoiKio brand. Open [`web/index.html`](web/index.html) in a browser (no build, no backend). It renders the [`web/sample-brief.json`](web/sample-brief.json) contract (matches [`docs/output-schema.md`](docs/output-schema.md)); to go live, swap the simulated run for a `/api/redteam` call returning that shape. See [`web/README.md`](web/README.md).

## How to run (usage)

See [`docs/runbook.md`](docs/runbook.md) for full provisioning steps. In short:

```bash
# 1. configure
cp .env.example .env        # fill in your Foundry / Search / OpenAI endpoints
pip install -r requirements.lock.txt   # fully pinned, shipped pin set (use the lock, not requirements.txt)

# 2. build the knowledge base from public docs
python scripts/setup_foundry_iq.py

# 3. red-team a thesis
python scripts/run_example.py --thesis examples/thesis.txt

# offline demo (no Azure/spend): drive everything from the saved run
FOUNDRY_IQ_BACKEND=mock python scripts/run_example.py --thesis examples/thesis.txt
```

> **Reproducible installs:** the dependency set the install path uses is **[`requirements.lock.txt`](requirements.lock.txt)** — every package pinned with `==`. `requirements.txt` is the unpinned source list; ship and install from the lock.

## Reliability gates & eval evidence

The reliability moat lives in [`src/citations.py`](src/citations.py) (see [`docs/reliability-spec.md`](docs/reliability-spec.md)): **compliance** (§3 — no BUY/SELL/HOLD instruction ships), **faithfulness** (§1 — every figure machine-checked against its citation quote; fabricated quote → crack rejected), **coverage** (§2 — uncovered claim → `data_gap`, not a false crack), **attack-bias** (§4 — cited-contradicted vs uncited-vulnerable disclosure). The behavioural eval suite [`scripts/run_evals.py`](scripts/run_evals.py) proves these end-to-end (E1–E9); captured results: **[`evals/EVIDENCE.md`](evals/EVIDENCE.md)** (9/9 green, incl. E2 missing-evidence and E8 determinism).

## Repository map

| Path | Contents |
|------|----------|
| `src/` | orchestration + the four agents + Foundry IQ client + citation guard + HTML renderer |
| `prompts/` | the system prompt, four agent prompts, and the six-lens chec