"""server.py — thin HTTP wrapper over agent.run (STORY-06.3.01, ADR-0010).

A deployable adapter, not business logic: `GET /health` for liveness and
`POST /analyze` (thesis -> cited Kintsugi brief) delegating to `agent.run`.
Run with: `uvicorn server:app --app-dir src --host 0.0.0.0 --port 8000`.
"""
from __future__ import annotations

import hmac
import os
import re

from fastapi import FastAPI, Header, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field, field_validator

import agent        # bare import — src/ is on sys.path (see Dockerfile --app-dir / PYTHONPATH)
import approvals    # human-in-the-loop run gate (Telegram), enforced server-side
import memory       # run-history store (STORY-08.2.03)

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


_EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")


class AnalyzeRequest(BaseModel):
    thesis: str = Field(..., min_length=1, description="The investment thesis to red-team.")
    run_token: str | None = Field(default=None, description="One-time token minted on Telegram approval.")


class ApprovalRequest(BaseModel):
    name: str = Field(..., min_length=1, max_length=120)
    email: str = Field(..., min_length=3, max_length=200)
    thesis: str = Field(..., min_length=1)

    @field_validator("email")
    @classmethod
    def _valid_email(cls, v: str) -> str:
        v = v.strip()
        if not _EMAIL_RE.match(v):
            raise ValueError("invalid email")
        return v


@app.get("/health")
def health() -> dict:
    return {"status": "ok"}


@app.post("/request-approval")
def request_approval(req: ApprovalRequest) -> dict:
    """Open a human-in-the-loop run gate: store a pending approval and push a Telegram request to the
    approver. Returns {approval_id} for the client to poll. 502 if the transport can't deliver."""
    try:
        approval_id = approvals.request_approval(req.name, req.email, req.thesis)
    except Exception:
        raise HTTPException(status_code=502, detail="could not send approval request")
    return {"approval_id": approval_id}


@app.get("/approval/{approval_id}")
def approval_status(approval_id: str) -> dict:
    """Poll the gate: {status: pending|approved|rejected[, run_token]}. The run_token appears only
    once approved, and is what /analyze requires."""
    a = approvals.get_approval(approval_id)
    if a is None:
        raise HTTPException(status_code=404, detail="unknown approval")
    return a


@app.post("/telegram/webhook")
async def telegram_webhook(
    request: Request,
    x_telegram_bot_api_secret_token: str | None = Header(default=None),
) -> dict:
    """Telegram callback sink: verify the shared secret header, then apply the approve/reject
    decision and acknowledge it back on the message."""
    expected = approvals.webhook_secret()
    got = x_telegram_bot_api_secret_token or ""
    if not expected or not hmac.compare_digest(got, expected):
        raise HTTPException(status_code=403, detail="forbidden")
    payload = await request.json()
    approvals.handle_callback(payload)
    return {"ok": True}


@app.post("/analyze")
def analyze(req: AnalyzeRequest) -> dict:
    """Run the four-agent red-team and return the scored, cited brief.

    SERVER-SIDE GATE: the repo + this endpoint are public, so the run is allowed only with a valid,
    unconsumed run_token minted on Telegram approval — consumed here (one-time). Without it, 403.
    Analysis, not advice — `agent.run` enforces the compliance gate; this layer adapts HTTP <-> the
    pipeline."""
    if not approvals.consume_token(req.run_token):
        raise HTTPException(status_code=403, detail="approval required: run_token missing, invalid, or already used")
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
