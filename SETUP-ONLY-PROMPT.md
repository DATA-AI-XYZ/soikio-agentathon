# Setup-only prompt — soikio-agentathon

Paste the block below into Claude Code (or run the commands yourself) from the repo root. This **only** sets up the project and installs dependencies — no app code, no Azure, no build.

---

Set up the project and install all dependencies. Do NOT write any application code, do NOT touch Azure, do NOT start the build. Stop when setup is verified.

## 0. Verify docs are present (already copied in — just confirm)
Check these exist; if any are missing, STOP and tell me:
- `prompts/` — system, bull, bear, caution, cio, lenses, extract
- `docs/` — scoring.md, reliability-spec.md, output-schema.md, report-spec.md, runbook.md, evaluation.md, kintsugi-principle.md, architecture.md, report.sample.html, and `adr/` 0001–0008
- `setup/CLAUDE.md`, `COMPLIANCE.md`, `requirements.txt`, `.env.example`
- `docs/design/` exists locally but is **gitignored** — confirm with `git check-ignore docs/design/00-plan.md` (should print the path).

## 1. Python environment + dependencies
1. Confirm Python 3.11+: `python --version`
2. Create + activate a venv:
   - Windows (PowerShell): `python -m venv .venv` then `.\.venv\Scripts\Activate.ps1`
   - Windows (Git Bash): `python -m venv .venv` then `source .venv/Scripts/activate`
3. `python -m pip install -U pip`
4. `pip install -r requirements.txt` (install latest compatible)
5. Lock the exact versions: `pip freeze > requirements.lock.txt`
6. Verify imports:
   ```
   python -c "import anthropic, openai, pydantic; from azure.search.documents import SearchClient; from azure.identity import DefaultAzureCredential; print('python deps OK')"
   ```
7. Create the env file (placeholders only — do NOT fill secrets): `copy .env.example .env` (PowerShell) / `cp .env.example .env` (bash)

## 2. PM-kit tooling (Node — for `pm:*` scripts only, not the app)
8. Ensure Node is on PATH (if `npm` is "not recognized" on Windows, add `C:\Program Files\nodejs`):
   - PowerShell: `$env:PATH = 'C:\Program Files\nodejs;' + $env:PATH`
   - Git Bash: `export PATH="/c/Program Files/nodejs:$PATH"`
9. `npm install`
10. `npm run pm:lint` then `npm run pm:dash` then `npm run pm:map`
    (validates PM artefacts + regenerates the dashboard/codebase map — PROJECT-CONTEXT.md was edited, so lint should pass clean.)

## 3. Report and STOP
Print: Python version, confirmation the venv + deps installed, the import-check result, and any `pm:lint` warnings. Then **STOP** — no application code, no Azure provisioning, no run. Do not `git push`.
