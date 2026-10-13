"""EHS Agent Console API — v2 + eng-1/2/3 (persist, CI, obs+auth)."""

from __future__ import annotations

import json
from contextlib import asynccontextmanager
from typing import Any

from fastapi import Depends, FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field

from .agent.llm import LLMCallError, LLMConfigError
from .agent.loop import run_agent, stream_agent
from .api.domain import router as domain_router
from .api.runs import router as runs_router
from .auth.deps import get_current_identity
from .auth.routes import router as auth_router
from .config import settings
from .db.seed import seed_if_empty
from .db.session import init_db
from .obs import RequestContextMiddleware
from .sessions import sessions


@asynccontextmanager
async def lifespan(_app: FastAPI):
    from pathlib import Path as _Path

    _Path("data").mkdir(parents=True, exist_ok=True)
    init_db()
    seed_if_empty()
    yield


app = FastAPI(
    title="EHS Agent Console",
    version="2.5.0",
    description="v2 + eng-1 persist + eng-2 pytest + eng-3 obs/auth + ind-01 durable runs",
    lifespan=lifespan,
)

# RequestContext outermost after CORS so access log sees final status
app.add_middleware(RequestContextMiddleware, log_level=settings.log_level)
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origin_list or ["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(domain_router)
app.include_router(auth_router)
app.include_router(runs_router)


class ChatRequest(BaseModel):
    message: str = Field(..., min_length=1)
    history: list[dict[str, Any]] = Field(default_factory=list)
    force_timeout: bool = False
    session_id: str | None = None
    # Kept for UI compatibility; ignored when JWT/API key present (server identity wins).
    tenant_id: str = "default"
    role: str = "ehs_engineer"


class ChatResponse(BaseModel):
    reply: str
    steps: list[dict[str, Any]]
    budget: dict[str, Any]
    identity: dict[str, Any] | None = None
    session_id: str | None = None


class SessionCreate(BaseModel):
    tenant_id: str = "default"
    role: str = "ehs_engineer"


@app.get("/health")
def health() -> dict[str, Any]:
    from .tools.hazard_ledger import list_corrective_tickets, query_hazard_ledger
    from .tools.registry import TOOLS

    hazards = query_hazard_ledger()
    tickets = list_corrective_tickets()
    return {
        "status": "ok",
        "version": "2.2.0",
        "curriculum": "ch1-9",
        "persistence": "sqlalchemy",
        "auth_mode": settings.auth_mode,
        "observability": "request_id+json_access_log",
        "durable_runs": True,
        "agent_trace": True,
        "hitl": settings.hitl_enabled,
        "hazard_count": hazards["count"],
        "ticket_count": tickets["count"],
        "as_of": hazards.get("as_of"),
        "llm_provider": settings.llm_provider,
        "llm_timeout_s": settings.llm_timeout_s,
        "llm_max_retries": settings.llm_max_retries,
        "tool_timeout_s": settings.tool_timeout_s,
        "max_agent_steps": settings.max_agent_steps,
        "tool_count": len(TOOLS),
        "eval_cmd": "python scripts/run_eval.py -v",
    }


@app.post("/api/sessions")
def create_session(
    body: SessionCreate,
    identity: dict[str, Any] = Depends(get_current_identity),
) -> dict[str, Any]:
    # Prefer authenticated identity over spoofable body fields when JWT/API key.
    if identity.get("auth_method") in {"jwt", "api_key"}:
        return sessions.create(tenant_id=identity["tenant_id"], role=identity["role"])
    return sessions.create(tenant_id=body.tenant_id, role=body.role)


@app.get("/api/sessions/{session_id}")
def get_session(
    session_id: str,
    identity: dict[str, Any] = Depends(get_current_identity),
) -> dict[str, Any]:
    _ = identity
    rec = sessions.get(session_id)
    if not rec:
        raise HTTPException(status_code=404, detail="session not found")
    return rec


@app.post("/api/chat")
async def api_chat(
    body: ChatRequest,
    identity: dict[str, Any] = Depends(get_current_identity),
) -> StreamingResponse:
    tenant_id = identity["tenant_id"]
    role = identity["role"]
    hist = list(body.history or [])
    if body.session_id:
        server_hist = sessions.history(body.session_id)
        if server_hist:
            hist = server_hist

    async def event_gen():
        final_reply = ""
        try:
            async for evt in stream_agent(
                body.message,
                hist,
                force_timeout=body.force_timeout,
                tenant_id=tenant_id,
                role=role,
            ):
                if evt["event"] == "done":
                    final_reply = evt["data"].get("reply") or ""
                    if body.session_id and final_reply:
                        try:
                            sessions.append_turn(body.session_id, body.message, final_reply)
                            evt["data"]["session_id"] = body.session_id
                            evt["data"]["session_turns"] = sessions.get(body.session_id).get("turns")
                        except KeyError:
                            evt["data"]["session_error"] = "invalid session_id"
                    evt["data"]["identity"] = {
                        "tenant_id": tenant_id,
                        "role": role,
                        "auth_method": identity.get("auth_method"),
                    }
                yield (
                    f"event: {evt['event']}\n"
                    f"data: {json.dumps(evt['data'], ensure_ascii=False)}\n\n"
                )
        except (LLMConfigError, LLMCallError) as exc:
            yield f"event: error\ndata: {json.dumps({'detail': str(exc)}, ensure_ascii=False)}\n\n"
        except Exception as exc:  # noqa: BLE001
            yield f"event: error\ndata: {json.dumps({'detail': str(exc)}, ensure_ascii=False)}\n\n"

    return StreamingResponse(
        event_gen(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
            "X-Tenant-Id": tenant_id,
            "X-Role": role,
        },
    )


@app.post("/api/chat/complete", response_model=ChatResponse)
async def api_chat_complete(
    body: ChatRequest,
    identity: dict[str, Any] = Depends(get_current_identity),
) -> ChatResponse:
    tenant_id = identity["tenant_id"]
    role = identity["role"]
    hist = list(body.history or [])
    if body.session_id:
        server_hist = sessions.history(body.session_id)
        if server_hist:
            hist = server_hist
    try:
        result = await run_agent(
            body.message,
            hist,
            force_timeout=body.force_timeout,
            tenant_id=tenant_id,
            role=role,
        )
    except (LLMConfigError, LLMCallError) as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc
    sid = body.session_id
    if sid and result.get("reply"):
        try:
            sessions.append_turn(sid, body.message, result["reply"])
        except KeyError:
            sid = None
    return ChatResponse(
        reply=result["reply"],
        steps=result["steps"],
        budget=result["budget"],
        identity=result.get("identity") or {
            "tenant_id": tenant_id,
            "role": role,
            "auth_method": identity.get("auth_method"),
        },
        session_id=sid,
    )
