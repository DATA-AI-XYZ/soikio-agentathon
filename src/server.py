"""server.py — thin HTTP wrapper over agent.run (STORY-06.3.01, ADR-0010).

A deployable adapter, not business logic: `GET /health` for liveness and
`POST /analyze` (thesis -> cited Kintsugi brief) delegating to `agent.run`.
Run with: `uvicorn server:app --app-dir src --host 0.0.0.0 --port 8000`.
"""
from __future__ import annotations

import os

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

import agent    # bare import — src/ is on sys.path (see Dockerfile --app-dir / PYTHONPATH)
import memory   # run-history store (STORY-08.2.03)

app = FastAPI(title="Soikio thesis red-team", version="1.0")

# CORS (STORY-08.3.01): the published UI is served from the GitHub Pages origin while this API
# lives on the Container App FQDN — so the browser `fetch POST /analyze` is a cross-origin request
# and is blocked without an explicit allow-origin + OPTIONS preflight. Allow the Pages origin
# (override via CORS_ALLOW_ORIGINS, comma-separated, e.g. to add http://localhost for dev).
# Scoped to the allow-list — never "*".
_cors_origins = [o.strip() for o in os.environ.get(
    "CORS_ALLOW_ORIGINS", "https://data-ai-xyz.github.io"
).split(",") if o.strip()]
app.add_middleware(
    CORSMiddleware,
    allow_origins=_cors_origins,
    allow_methods=["GET", "POST", "OPTIONS"],
    allow_headers=["Content-Type"],
)

# App Insights via OpenTelemetry (STORY-06.3.02 AC-2): when the connection string is
# present, emit request traces + latency. No-op locally (var unset) so dev/tests are unaffected.
_appi = os.environ.get("APPLICATIONINSIGHTS_CONNECTION_STRING", "").strip()
if _appi:
    from azure.monitor.opentelemetry import configure_azure_monitor

    configure_azure_monitor(connection_string=_appi)
    from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor

    FastAPIInstrumentor.instrument_app(app)


class AnalyzeRequest(BaseModel):
    thesis: str = Field(..., min_length=1, description="The investment thesis to red-team.")


@app.get("/health")
def health() -> dict:
    return {"status": "ok"}


@app.post("/analyze")
def analyze(req: AnalyzeRequest) -> dict:
    """Run the four-agent red-team and return the scored, cited brief.

    Analysis, not advice — `agent.run` enforces the compliance gate; this layer
    only adapts HTTP <-> the pipeline."""
    return agent.run(req.thesis)


@app.get("/api/runs")
def list_runs(ticker: str | None = None, limit: int = 50) -> list:
    """History index: recent stored runs (date·ticker·verdict·confidence). Backs web/history.html."""
    return memory.get_store().list_runs(ticker=ticker, limit=limit)


@app.get("/api/runs/{run_id}")
def get_run(run_id: str) -> dict:
    """Fetch one stored run's full brief by id; 404 (not 500) when unknown."""
    run = memory.get_store().get_run(run_id)
    if run is None:
        raise HTTPException(status_code=404, detail="run not found")
    return run
