# Web frontend

A self-contained demo frontend for the thesis red-team — submit → run → cited conflict map. SoiKio brand (v1.3.4 void). No build step, no backend required: open `index.html` in a browser.

## What it is
- `index.html` — the three-screen flow (submit · run · output), styled in the SoiKio brand. Runs standalone with illustrative MSFT sample data.
- `sample-brief.json` — the **output contract** the report renders from. Shape matches [`../docs/output-schema.md`](../docs/output-schema.md) (thesis · `thesis_robustness` · `confidence` · `conflict_map` · `run` · `citations`).

## Integration point (frontend → backend)
Today the run is **simulated** and the report uses bundled sample data. To wire it to the live pipeline, replace the simulated run in `index.html` with a call to the orchestration API and render the returned brief:

```js
// submit thesis → kick off a run → poll → render
const res  = await fetch('/api/redteam', { method:'POST', body: JSON.stringify({ ticker, thesis }) });
const brief = await res.json();   // shape = sample-brief.json / docs/output-schema.md
renderReport(brief);              // deterministic render of the conflict map
```

The backend (`src/agent.py` → `render.py`) produces exactly the `sample-brief.json` shape, so the frontend is contract-compatible with the live API.

## Note
This applies the proprietary SoiKio brand — keep that in mind before making the repo public.
