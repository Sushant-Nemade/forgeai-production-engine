from __future__ import annotations

import os
from contextlib import asynccontextmanager

from fastapi import Depends, FastAPI, HTTPException, Request
from fastapi.responses import HTMLResponse
from fastapi.security import HTTPAuthorizationCredentials
from prometheus_fastapi_instrumentator import Instrumentator
from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import AsyncSession

from core_engine.orchestrator import Orchestrator
from .auth import bearer, create_access_token, require_user, verify_password
from .db import get_session
from .models import FactoryRun
from .schemas import RunRequest, RunResponse, TokenResponse

DEMO_PASSWORD_HASH = os.environ.get("DEMO_PASSWORD_HASH")
DEMO_USER = os.environ.get("DEMO_USER", "admin")


@asynccontextmanager
async def lifespan(app: FastAPI):
    yield


app = FastAPI(title="ForgeAI Control Plane", version="1.0.0", lifespan=lifespan)
Instrumentator().instrument(app).expose(app, endpoint="/metrics")


@app.get("/health", tags=["system"])
async def health() -> dict[str, str]:
    return {"status": "ok"}


@app.get("/ready", tags=["system"])
async def ready(session: AsyncSession = Depends(get_session)) -> dict[str, str]:
    await session.execute(text("SELECT 1"))
    return {"status": "ready"}


@app.get("/", response_class=HTMLResponse, include_in_schema=False)
async def dashboard() -> str:
    return HTML_PAGE


@app.post("/api/auth/token", response_model=TokenResponse, tags=["auth"])
async def token(request: Request) -> TokenResponse:
    body = await request.json()
    if not DEMO_PASSWORD_HASH or body.get("username") != DEMO_USER or not verify_password(body.get("password", ""), DEMO_PASSWORD_HASH):
        raise HTTPException(status_code=401, detail="Invalid credentials")
    return TokenResponse(access_token=create_access_token(DEMO_USER))


@app.post("/api/runs", response_model=RunResponse, tags=["factory"])
async def create_run(
    payload: RunRequest,
    credentials: HTTPAuthorizationCredentials | None = Depends(bearer),
    session: AsyncSession = Depends(get_session),
) -> RunResponse:
    require_user(credentials)
    result = await Orchestrator().run(payload.brief, source_root=".")
    run = FactoryRun(brief=payload.brief, state=result.state, result={"transitions": [str(s) for s in result.transitions], "artifacts": result.artifacts, "errors": result.errors})
    session.add(run)
    await session.commit()
    await session.refresh(run)
    return RunResponse(id=run.id, state=result.state, result=run.result)


@app.get("/api/runs", response_model=list[RunResponse], tags=["factory"])
async def list_runs(
    credentials: HTTPAuthorizationCredentials | None = Depends(bearer),
    session: AsyncSession = Depends(get_session),
) -> list[RunResponse]:
    require_user(credentials)
    rows = (await session.execute(select(FactoryRun).order_by(FactoryRun.created_at.desc()).limit(50))).scalars().all()
    return [RunResponse(id=r.id, state=r.state, result=r.result) for r in rows]


HTML_PAGE = """<!doctype html><html><head><meta charset='utf-8'><meta name='viewport' content='width=device-width,initial-scale=1'><title>ForgeAI</title><style>body{font-family:system-ui;background:#0b1020;color:#eef;padding:4rem;max-width:900px;margin:auto}textarea{width:100%;min-height:140px;background:#121a2f;color:#fff;border:1px solid #334;padding:1rem;border-radius:12px}button{margin-top:1rem;padding:.8rem 1.2rem;border:0;border-radius:10px;background:#6d5dfc;color:#fff;font-weight:700}.card{background:#121a2f;padding:1.5rem;border-radius:16px;margin-top:1.5rem}code{color:#9fe3ff}</style></head><body><h1>ForgeAI</h1><p>Autonomous vibe-to-production control plane.</p><div class='card'><h2>Factory pipeline</h2><p><code>RECEIVED → SCHEMA_MAPPED → API_GENERATED → QA_SCANNED → DEPLOYABLE</code></p><textarea id='brief'>resource: invoice; fields: customer_id(string), amount(number), paid(boolean)</textarea><button onclick='run()'>Run factory</button><pre id='out'></pre></div><script>async function run(){const out=document.getElementById('out');out.textContent='API authentication is required for programmatic runs. Use /docs or configure a token.'}</script></body></html>"""
