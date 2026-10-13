"""EHS Agent Console API — v2 curriculum (Ch1–9)."""

from __future__ import annotations

import json
from typing import Any

from fastapi import FastAPI, Header, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field

from .agent.llm import LLMCallError, LLMConfigError
from .agent.loop import run_agent, stream_agent
from .api.domain import router as domain_router
from .auth.tenant import resolve_identity
from .config import settings
from .sessions import sessions

app = FastAPI(
    title="EHS Agent Console",
    version="2.0.0",
    description="v2: domain → agent → SSE → reliability → eval → RAG → session → tenant → interview",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origin_list or ["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(domain_router)


class ChatRequest(BaseModel):
    message: str = Field(..., min_length=1)
    history: list[dict[str, Any]] = Field(default_factory=list)
    force_timeout: bool = False
    session_id: str | None = None
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
        "version": "2.0.0",
        "curriculum": "ch1-9",
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
def create_session(body: SessionCreate) -> dict[str, Any]:
    return sessions.create(tenant_id=body.tenant_id, role=body.role)


@app.get("/api/sessions/{session_id}")
def get_session(session_id: str) -> dict[str, Any]:
    rec = sessions.get(session_id)
    if not rec:
        raise HTTPException(status_code=404, detail="session not found")
    return rec


@app.post("/api/chat")
async def api_chat(body: ChatRequest) -> StreamingResponse:
    identity = resolve_identity(body.tenant_id, body.role)
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
                tenant_id=body.tenant_id,
                role=body.role,
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
            "X-Tenant-Id": identity["tenant_id"],
            "X-Role": identity["role"],
        },
    )


@app.post("/api/chat/complete", response_model=ChatResponse)
async def api_chat_complete(body: ChatRequest) -> ChatResponse:
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
            tenant_id=body.tenant_id,
            role=body.role,
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
        identity=result.get("identity"),
        session_id=sid,
    )
