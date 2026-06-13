# CLAUDE.md

<!-- This is the always-on Tier-1 root file: loaded every session, so every line
     costs context on every task. Keep it lean — only rules relevant to almost
     ANY task here. Signpost folder-scoped files in plain words ("when editing X,
     read x/CLAUDE.md"); do NOT use @import (it re-bloats the always-loaded
     context). Place a rule here only when a miss is serious/irreversible;
     recoverable, area-local rules go in a folder-scoped CLAUDE.md. -->

<!-- PM-KIT-BLOCK -->
This repo uses the Tandem. PM artefacts live under `_00-Project-Management/`; read `_00-Project-Management/CLAUDE.md` before touching them. Non-negotiables: closed 9-value status enum, quoted ISO-8601 timestamps, every Story has a paired Testplan, one hat per session. Run `npm run pm:lint` before committing PM edits.

<!-- PROJECT-MAP -->
Top-level layout: see [`CODEBASE-MAP.md`](./CODEBASE-MAP.md) (regenerate with `npm run pm:map`).

<!-- BUILD-GUIDE -->
**Build & setup:** `setup/CLAUDE.md` is the authoritative build guide (invariants + file-by-file plan); algorithm in `docs/scoring.md`, reliability gates in `docs/reliability-spec.md`. The product is a four-agent **thesis red-team** (Bull/Bear/Caution + CIO, on Claude) that tests a user's investment thesis against public filings via Foundry IQ and returns a cited **Kintsugi conflict map** + robustness verdict (Holds/Contested/Breaks). **Analysis-not-advice; never BUY/SELL/HOLD.** Internal design notes live in `docs/design/` (gitignored — clean-room).

<!-- CRITICAL-GOTCHAS -->
- The **app is Python**; `package.json` / Node exist only to run the PM kit's `pm:*` scripts — don't treat this as a Node app.
- Microsoft Foundry IQ / Azure credentials live in `.env` (gitignored, `.claudeignore`'d) — required to run the agent; never commit or paste them into chat.
- PM tooling needs Node on PATH. On Windows bash/PowerShell, `C:\Program Files\nodejs` is often absent — prepend it before `npm run pm:*` if you hit "command not found".

<!-- REFERENCE-ORDER -->
When unsure of a rule: this file → `_00-Project-Management/CLAUDE.md` → `_00-Project-Management/90-Standards/SOP.md` §16.
