"""server.py — thin HTTP wrapper over agent.run (STORY-06.3.01, ADR-0010).

A deployable adapter, not business logic: `GET /health` for liveness and
`POST /analyze` (thesis -> cited Kintsugi brief) delegating to `agent.run`.
Run with: `uvicorn server:app --app-dir src --host 0.0.0.0 --port 8000`.
"""
from __future__ import annotations

import os

from fastapi import FastAPI
from pydantic import BaseModel, Field

import agent  # bare import — src/ is on sys.path (see Dockerfile --app-dir / PYTHONPATH)

app = FastAPI(title="Soikio thesis red-team", version="1.0")

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
