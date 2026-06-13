---
schema: v1
generated_by: curate-toolkit
generated_at: '2026-06-12T23:08:10+01:00'
project_type: automation
---

# Toolkit Relevance Overlay — soikio-agentathon

**Project shape (ranking signal):** `automation` — a four-agent **thesis red-team** (Bull / Bear /
Caution + CIO) on **Claude/Anthropic**, testing an investment thesis against public filings via
**Microsoft Foundry IQ on Azure AI Search**. Pipeline-invoked Python 3.11+; emits a generated
**static HTML report** (Kintsugi conflict map). **No interactive web UI, no app DB, no frontend.**
Secrets: Azure Entra ID / managed identity + `ANTHROPIC_API_KEY`. CI/CD: GitHub Actions (not yet
configured). Dev box: **Windows 11 / PowerShell** with documented Node-on-PATH gotchas.

**Sub-agent map (preferred specialists, from PROJECT-CONTEXT):** `backend → debugger / general-purpose`,
`infra → deployment-engineer`, `data → general-purpose`, `docs → technical-writer`. `frontend` row
pruned (no UI surface).

> Ranking is judgment-led against the above. **HIGH** = reach for routinely on this project.
> **MED** = conditionally useful for a phase or task type. **LOW** = off-stack / not applicable.
> `installed: false` rows are explicit gap markers (see Gaps).

---

## Agents

User-level agents at `C:\Users\PeterPirisola\.claude\agents\` (44 found).

| id | rank | installed | rationale |
|----|------|-----------|-----------|
| debugger | HIGH | true | Named `backend` sub-agent; debugging the Python multi-agent pipeline is core. |
| deployment-engineer | HIGH | true | Named `infra` sub-agent; Azure / Foundry deploy, packaging, GitHub Actions CI/CD. |
| technical-writer | HIGH | true | Named `docs` sub-agent; docs/scoring.md, reliability-spec, report copy. |
| llm-architect | HIGH | true | RAG + multi-model LLM systems — maps directly to 4-agent Claude red-team over Foundry IQ retrieval. |
| prompt-engineer | HIGH | true | Product is prompt-heavy (six analytical lenses, CIO synthesis); prompt design is on the critical path. |
| mcp-developer | MED | true | Foundry IQ / Azure retrieval integration patterns; useful if grounding moves to an MCP surface. |
| context7 | MED | true | Pulls current `anthropic` / `azure-search-documents` SDK docs — reach for when writing SDK calls. |
| code-reviewer | MED | true | Cross-cutting Python review; routine but phase-bound, not every session. |
| error-detective | MED | true | Cross-cutting failure-cascade analysis for the retrieval + agent chain. |
| refactoring-specialist | MED | true | Cross-cutting code-quality; useful as the agent core matures. |
| code-simplifier | MED | true | Cross-cutting clarity passes on Python. |
| security-engineer | MED | true | Azure Entra/managed-identity + API-key handling; conditional (review phases). |
| git-workflow-manager | MED | true | Cross-cutting branch/merge hygiene; aligns with PM-kit phase branches. |
| github-actions-expert | MED | true | CI/CD is GitHub Actions (planned-but-unconfigured) — relevant when wiring it. |
| test-runner | MED | true | Runs/diagnoses Python tests for the reliability gates. |
| test-generator | MED | true | Generates test cases against reliability-spec; phase-bound. |
| bug-raiser | MED | true | Writes BUG files — aligns with the kit's auto-raise flow (path convention differs; verify). |
| test-plan-writer | MED | true | Writes paired Testplans — aligns with kit's Story→Testplan rule (verify path mapping). |
| diagram-architect | MED | true | Conflict-map / architecture diagrams for docs and the HTML report. |
| documentation-engineer | MED | true | Doc-system structure; secondary to technical-writer (the named docs agent). |
| performance-engineer | LOW | true | Batch analysis tool, not latency-bound; retrieval tuning handled in-spec. |
| unused-code-cleaner | LOW | true | Niche maintenance; not routine on a young hackathon codebase. |
| test-file-scaffolder | LOW | true | Playwright/Jest stub scaffolder — JS test stack, not pytest. |
| playwright-tester | LOW | true | Browser E2E; no interactive web UI to drive. |
| api-designer | LOW | true | No end-user API surface (pipeline-invoked). |
| frontend-developer | LOW | true | No frontend. |
| fullstack-developer | LOW | true | No fullstack / UI layer. |
| ui-designer | LOW | true | No UI surface. |
| ui-ux-designer | LOW | true | No UI surface. |
| react-specialist | LOW | true | No React. |
| react-performance-optimizer | LOW | true | No React. |
| web-vitals-optimizer | LOW | true | No web app / Core Web Vitals surface. |
| web-accessibility-checker | LOW | true | Static report only; off primary stack. |
| javascript-pro | LOW | true | App is Python; Node exists only to run the PM kit. |
| build-engineer | LOW | true | No JS bundler/build to optimize. |
| seo-specialist | LOW | true | No public web surface to rank. |
| seo-analyzer | LOW | true | No public web surface to rank. |
| content-marketer | LOW | true | Off-stack (marketing). |
| product-manager | LOW | true | PM owned by the Tandem kit; generic PM agent off-stack here. |
| power-bi-data-modeling-expert | LOW | true | No Power BI. |
| power-bi-dax-expert | LOW | true | No Power BI. |
| power-bi-performance-expert | LOW | true | No Power BI. |
| power-bi-visualization-expert | LOW | true | No Power BI. |
| power-platform-expert | LOW | true | No Power Platform. |
| power-platform-mcp-integration-expert | LOW | true | No Power Platform. |

## Commands

User-level commands at `C:\Users\PeterPirisola\.claude\commands\` (24 found).

| id | rank | installed | rationale |
|----|------|-----------|-----------|
| clean | HIGH | true | Fixes black / isort / flake8 / mypy — exactly this project's Python toolchain. |
| secrets-scanner | HIGH | true | Real secret surface (Azure creds + `ANTHROPIC_API_KEY` in gitignored `.env`). |
| security-audit | MED | true | Credential / managed-identity surface; conditional review pass. |
| debug-error | MED | true | Python error diagnosis; routine during build. |
| dependency-audit | MED | true | `requirements.txt` / lock auditing. |
| update-dependencies | MED | true | Python dep bumps (anthropic, azure-* SDKs). |
| generate-tests | MED | true | Test scaffolding against reliability gates. |
| write-tests | MED | true | Test authoring for the Python pipeline. |
| test-coverage | MED | true | Coverage signal for reliability-spec gates. |
| refactor-code | MED | true | Cross-cutting code quality. |
| explain-code | MED | true | Comprehension of agent/retrieval logic. |
| check-file | MED | true | Single-file analysis during build. |
| directory-deep-dive | MED | true | Onboarding into the Python module layout. |
| code-review | MED | true | Cross-cutting review pass. |
| fix-issue | MED | true | GitHub issue → fix flow. |
| ultra-think | MED | true | Deep reasoning for scoring/conflict-map design. |
| context-prime | MED | true | Session priming; overlaps Tandem session-start. |
| prime | MED | true | Session priming for complex tasks. |
| start | MED | true | Task orchestration. |
| todo | MED | true | Lightweight task tracking. |
| git-status | MED | true | Git state; cross-cutting. |
| clean-branches | MED | true | Branch hygiene across phase branches. |
| memory-spring-cleaning | MED | true | Memory upkeep; periodic. |
| screenshot-analyzer | LOW | true | Extracts features from product screenshots — no UI to screenshot. |

## Skills

Tandem PM kit + curated user-level skills ranked individually. Plugin-bundled skill **suites**
(superpowers, astronomer-data, pinecone, chrome-devtools, frontend-design, etc.) are ranked at the
plugin granularity in **Plugins** below — their member skills inherit the plugin's tier. See caveats.

### Tandem (PM operating kit — the repo runs on this)

| id | rank | installed | rationale |
|----|------|-----------|-----------|
| Tandem:core | HIGH | true | The operating rules (status enum, timestamps, Story↔Testplan, gates) — load whenever touching PM. |
| Tandem:session-start | HIGH | true | Loads active context at session open — routine entry point. |
| Tandem:execute-story | HIGH | true | Primary execution loop for stories. |
| Tandem:run-testplan | HIGH | true | Runs the paired testplan — mandatory per Story↔Testplan rule. |
| Tandem:close-out-story | HIGH | true | DoD gate + status flip + dashboard regen. |
| Tandem:split-into-features | HIGH | true | Epic→Feature decomposition; active planning. |
| Tandem:split-into-stories | HIGH | true | Feature→Story+Testplan; active planning. |
| Tandem:refine-backlog | HIGH | true | DoR gating before execution. |
| Tandem:curate-toolkit | HIGH | true | This skill — toolkit relevance ranking. |
| Tandem:weekly-monitor | MED | true | Friday cadence MONITOR update. |
| Tandem:draft-prd | MED | true | PRD authoring; phase-bound. |
| Tandem:draft-epic | MED | true | Epic authoring; phase-bound. |
| Tandem:draft-okrs | MED | true | Quarterly strategy cadence. |
| Tandem:execution-strategist | MED | true | Dry-run batch planning before execute-batch. |
| Tandem:execute-batch | MED | true | Runs a chat/batch of stories. |
| Tandem:start-phase | MED | true | Phase opener (branch cut + gate). |
| Tandem:close-phase | MED | true | Phase retro + gated merge. |
| Tandem:critique | MED | true | Advisory artefact quality pass. |
| Tandem:peer-review | MED | true | On-demand code peer review. |
| Tandem:document | MED | true | Generates the markdown doc set. |
| Tandem:fill-claude-md | MED | true | Maintains CLAUDE.md context. |
| Tandem:monthly-retro | MED | true | Monthly cadence retro. |
| Tandem:reflect | MED | true | Session reflection. |
| Tandem:write-outcomes | MED | true | Outcome capture. |

### User-level skills (`C:\Users\PeterPirisola\.claude\skills\`)

| id | rank | installed | rationale |
|----|------|-----------|-----------|
| systematic-debugging | HIGH | true | Rigid debugging process; applies regardless of stack and is routine for the agent pipeline. |
| security-best-practices | HIGH | true | Explicitly supports Python; real credential/secret surface (Azure + API key). |
| powershell-windows | HIGH | true | Dev box is Windows/PowerShell with documented Node-on-PATH gotchas in PROJECT-CONTEXT. |
| verification-before-completion | HIGH | true | Maps to the kit's DoD / reliability-gate "evidence before claims" culture. |
| clean-code | MED | true | Pragmatic standards apply to Python. |
| anti-drift | MED | true | Scope discipline; aligns with PM-kit gating. |
| find-bugs | MED | true | Branch-change bug/security review. |
| error-resolver | MED | true | First-principles error diagnosis; cross-cutting. |
| code-review | MED | true | Cross-cutting review (Sentry practices). |
| code-review-checklist | MED | true | Review checklist; phase-bound. |
| code-reviewer | MED | true | Multi-language review incl. Python. |
| commit-work | MED | true | Git commit hygiene. |
| create-pr | MED | true | PR authoring. |
| git-pushing | MED | true | Push workflow. |
| github-actions-creator | MED | true | CI/CD is GitHub Actions (to be configured). |
| best-practices | MED | true | Security/quality slice useful; web-compat slice off-stack. |
| writing-plans | MED | true | Planning; overlaps Tandem planning skills. |
| create-plan | MED | true | Planning; overlaps Tandem. |
| concise-planning | MED | true | Atomic checklist planning. |
| mermaid-diagrams | MED | true | Diagrams for docs / conflict-map narrative. |
| testing-patterns | LOW | true | Jest-specific; Python project uses pytest. |
| javascript-mastery | LOW | true | App is Python. |
| draw-io | LOW | true | Heavier diagramming; mermaid covers the need. |
| obsidian-bases | LOW | true | Obsidian-specific; not in this workflow. |
| obsidian-markdown | LOW | true | Obsidian-specific; not in this workflow. |

## Plugins

Installed plugins at `C:\Users\PeterPirisola\.claude\plugins\cache\`. Bundled skills/agents inherit
the plugin's tier unless individually re-ranked above.

| id | rank | installed | rationale |
|----|------|-----------|-----------|
| Tandem | HIGH | true | The PM operating kit this repo is built on (`_00-Project-Management/`). |
| superpowers | HIGH | true | Process skills (brainstorming, TDD, systematic-debugging, writing/executing-plans) enforced at session start. |
| context7 | MED | true | Live SDK docs for `anthropic` / `azure-search-documents` — reach for when coding SDK calls. |
| security-guidance | MED | true | Python-supported security review for the credential surface. |
| agent-sdk-dev | MED | true | Claude multi-agent build patterns; product uses raw `anthropic` SDK + Foundry, so adjacent not exact. |
| claude-md-management | MED | true | Repo carries several CLAUDE.md files to audit/maintain. |
| code-simplifier | MED | true | Cross-cutting Python clarity passes. |
| hookify | MED | true | Could encode project guardrails as hooks (e.g. never-BUY/SELL/HOLD, clean-room). |
| data-engineering | LOW | true | Airflow/dbt/Astro orchestrators — off-stack; index wrangling is Azure AI Search, not these. |
| pinecone | LOW | true | Vector store is Azure AI Search (Foundry IQ), not Pinecone. |
| chrome-devtools-mcp | LOW | true | Static report only; the zero-dep CDP smoke (ADR-0038) needs no MCP. |
| playwright | LOW | true | Browser E2E; no interactive web UI. |
| frontend-design | LOW | true | No frontend. |
| supabase | LOW | true | No app DB / Supabase. |
| firebase | LOW | true | No Firebase. |
| plugin-dev | LOW | true | Not authoring plugins here. |
| skill-creator | LOW | true | Consuming, not authoring, skills. |
| playground | LOW | true | Sandbox/demo; not on the build path. |

## Gaps (referenced but not installed)

| id | kind | rank | installed | referenced in | rationale |
|----|------|------|-----------|---------------|-----------|
| python-pro | agent | LOW | false | PROJECT-CONTEXT.md § Sub-agent mapping (`backend` row) | GAP — not installed; backend work degrades to `debugger` / `general-purpose` fallback. |
| data-engineer (data specialist) | agent | LOW | false | PROJECT-CONTEXT.md § Sub-agent mapping (`data` row: "swap in a data specialist if installed") | GAP — no standalone data agent on disk; `data` work degrades to `general-purpose`. |
| general-purpose | agent | n/a | true (built-in) | Sub-agent map fallback (backend/data) | Built-in executor fallback — always available; not a gap. |
