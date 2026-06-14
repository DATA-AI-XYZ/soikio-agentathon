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

The six lenses each stance applies: **Macro · Fundamental · Technical/Quant · Risk · Event-driven · Supply-chain**.

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