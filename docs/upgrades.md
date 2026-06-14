# Upgrades — three additions

Three capabilities added on top of the core thesis red-team, each wired to the existing design.

## 1. Frontend, auto-deployed (no human in the loop)
- **What:** the standalone UI in `web/` (submit → run → cited conflict map) is published to **GitHub Pages** by `.github/workflows/deploy-pages.yml` on every push.
- **Why static, not Power Pages:** static HTML on Pages deploys hands-free via CI; Power Pages needs Dataverse + portal config + licensing (human-in-the-loop). Static wins for speed/automation.
- **One-time enable:** repo **Settings → Pages → Source = "GitHub Actions"**. After that, pushes to `main` deploy automatically; the live URL appears in the Action's summary.
- Contract: the page renders `web/sample-brief.json` (= `docs/output-schema.md`); swap the simulated run for a `fetch('/api/redteam')` to go live.

## 2. Memory / persistence
- **What:** `src/memory.py` stores every run's brief (thesis + conflict map + citations) and recalls them.
- **API:** `save_brief(brief) -> run_id` · `get_run(id)` · `list_runs(ticker?)` · `prior_run(ticker)`.
- **Backends:** `LocalJsonStore` (offline default — `runs/*.json` + `index.jsonl`) and `BlobStore` (Azure Blob, `MEMORY_BACKEND=blob`). **Append-only** — a saved brief is never overwritten (audit integrity). This is the seam the production Cosmos/PostgreSQL audit trail (see `_00-Project-Management/20-Requirements/SPEC-production-azure-architecture.md`) slots behind.
- **Two payoffs:** (a) history / audit trail; (b) `prior_run()` feeds the *resolution loop* — a re-run can reference the last verdict and show what changed.
- Verified: `python src/memory.py` runs the offline smoke test.

## 3. Domain agents (six specialists)
- **What:** six per-lens specialist agents (Macro · Fundamental · Technical/Quant · Risk · Event-driven · Supply-chain) that gather **grounded, cited** evidence *before* the debate. Prompts in `prompts/domains.md`; orchestration in `src/domains.py`.
- **New topology:** `extract claims → domains.run_all() → Bull/Bear/Caution → CIO`. The domain agents produce the `domain_findings` already defined in `docs/output-schema.md`; the stances argue over them.
- **Discipline kept:** each specialist runs the **coverage probe** first (`coverage:false` → data gap, not invented evidence) and cites quotes only from retrieved extracts — so more agents means more depth and a cleaner evidence trail, not more opinions.
- Verified: `import domains` exposes the six `LENSES`.

## How they fit together
```
thesis ─▶ extract.py ─▶ domains.run_all (6 specialists, grounded)
                              │  domain_findings
                              ▼
                 Bull · Bear · Caution  ─▶  CIO (conflict map + deterministic scorer)
                              │
                              ▼
                 render.py ─▶ web/ UI        memory.save_brief() ─▶ audit trail
```

## Clean-room note
All three are generic, freshly-written code/prompts (no SoiKio proprietary content). The `web/` UI applies the SoiKio *brand* (the author's own) — keep that in mind before flipping the repo public.
