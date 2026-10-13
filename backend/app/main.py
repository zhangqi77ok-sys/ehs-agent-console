"""EHS Agent Console API — Chapter 1 focus: domain REST. Agent/SSE kept for later chapters."""

from __future__ import annotations

import json
from typing import Any

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field

from .agent.llm import LLMCallError, LLMConfigError
from .agent.loop import run_agent, stream_agent
from .api.domain import router as domain_router
from .config import settings

app = FastAPI(
    title="EHS Agent Console",
    version="1.0.0-ch1",
    description="Chapter 1: EHS domain foundation (hazards + CAPA REST). Agent UI returns in Chapter 2.",
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


class ChatResponse(BaseModel):
    reply: str
    steps: list[dict[str, Any]]
    budget: dict[str, Any]


@app.get("/health")
def health() -> dict[str, Any]:
    from .tools.hazard_ledger import query_hazard_ledger, list_corrective_tickets
    from .tools.registry import TOOLS

    hazards = query_hazard_ledger()
    tickets = list_corrective_tickets()
    return {
        "status": "ok",
        "chapter": 1,
        "focus": "domain",
        "hazard_count": hazards["count"],
        "ticket_count": tickets["count"],
        "as_of": hazards.get("as_of"),
        "llm_provider": settings.llm_provider,
        "tool_count": len(TOOLS),
        "note": "Chapter 1 = domain REST + thin console. Agent chat is Chapter 2+.",
    }


# --- Chapter 2+ (kept, not the Ch1 UI path) ---


@app.post("/api/chat")
async def api_chat(body: ChatRequest) -> StreamingResponse:
    async def event_gen():
        try:
            async for evt in stream_agent(
                body.message, body.history, force_timeout=body.force_timeout
            ):
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
        },
    )


@app.post("/api/chat/complete", response_model=ChatResponse)
async def api_chat_complete(body: ChatRequest) -> ChatResponse:
    try:
        result = await run_agent(
            body.message, body.history, force_timeout=body.force_timeout
        )
    except (LLMConfigError, LLMCallError) as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc
    return ChatResponse(**result)
