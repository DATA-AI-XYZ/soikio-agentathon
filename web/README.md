# Web frontend

A self-contained demo frontend for the thesis red-team — submit → run → cited conflict map. SoiKio brand (v1.3.4 void). No build step, no backend required: open `index.html` in a browser.

## What it is
- `index.html` — the three-screen flow (submit · run · output), styled in the SoiKio brand. Runs standalone with illustrative MSFT sample data.
- `sample-brief.json` — the **output contract** the report renders from. Shape matches [`../docs/output-schema.md`](../docs/output-schema.md) (thesis · `thesis_robustness` · `confidence` · `conflict_map` · `run` · `citations`).

## Integration point (frontend → backend) — STORY-08.3.01
The UI is now **wired to the live backend**. `runIt()` POSTs the thesis to `${API_BASE}/analyze` and renders the returned brief via `renderBrief()` (binds verdict / confidence / data-completeness / the conflict-map cracks, and reuses the domain + reviewer panels). The backend (`src/server.py` → `agent.run` → `render.py`) returns exactly the `sample-brief.json` / [`../docs/output-schema.md`](../docs/output-schema.md) shape, so the render is contract-compatible.

**Mode select — `API_BASE`:**
- **Demo mode (default):** `API_BASE` is empty → the run is simulated and the report shows the bundled illustrative sample. This is what the public Pages site serves so it works with no backend.
- **Live mode:** set `window.SOIKIO_API` to the deployed backend origin (inject a `<script>window.SOIKIO_API='https://…azurecontainerapps.io'</script>` before this page's script, or a one-line build step). Then a real `POST /analyze` runs.

**States (no silent failure):** a visible **loading** banner during the call; an **error** banner on a failed/unreachable backend (falls back to the sample, never a blank screen); an **empty/unexpected-result** message if the brief is malformed.

### CORS seam (cross-origin)
The published UI is served from the **GitHub Pages origin** (`https://data-ai-xyz.github.io`) while `/analyze` lives on a **different origin** — the **Azure Container App FQDN** (`https://ca-soikio-prod-eus2.<hash>.eastus2.azurecontainerapps.io`). A browser `fetch` across those origins is a **CORS** request, so the backend **must** send `Access-Control-Allow-Origin` for the Pages origin (and handle the `OPTIONS` preflight for the JSON `POST`):

```python
# src/server.py — FastAPI CORS, allow-list scoped to the Pages origin (not "*")
from fastapi.middleware.cors import CORSMiddleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["https://data-ai-xyz.github.io"],   # the Pages origin only
    allow_methods=["POST", "OPTIONS"],
    allow_headers=["Content-Type"],
)
```

Without this, the live call is blocked by the browser even though the API is up. Keep the allow-list **scoped to the Pages origin** — do not use `*` (the reviewer-checklist item). This CORS middleware on the deployed backend is an **operator/ops step** (paired with TESTPLAN-08.3.01 TC-04, the live `curl`).

## Note
This applies the proprietary SoiKio brand — keep that in mind before making the repo public.
