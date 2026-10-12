"""EHS Agent Console API."""

from __future__ import annotations

import json
from typing import Any

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field

from .agent.llm import LLMCallError, LLMConfigError
from .agent.loop import run_agent, stream_agent
from .config import settings
from .tools.hazard_ledger import list_tickets, query_hazard_ledger

app = FastAPI(title="EHS Agent Console", version="0.3.1")

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origin_list or ["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


class ChatRequest(BaseModel):
    message: str = Field(..., min_length=1)
    history: list[dict[str, Any]] = Field(default_factory=list)
    # Teaching drill: frontend 「练习：强制超时」 — tiny LLM timeout for this turn only.
    force_timeout: bool = False


class ChatResponse(BaseModel):
    reply: str
    steps: list[dict[str, Any]]
    budget: dict[str, Any]


@app.get("/health")
def health() -> dict[str, Any]:
    return {
        "status": "ok",
        "llm_provider": settings.llm_provider,
        "llm_timeout_s": settings.llm_timeout_s,
        "llm_max_retries": settings.llm_max_retries,
        "llm_retry_backoff_s": settings.llm_retry_backoff_s,
        "tool_timeout_s": settings.tool_timeout_s,
    }


@app.get("/api/hazards")
def api_hazards(keyword: str = "", status: str = "", level: str = "") -> dict:
    return query_hazard_ledger(keyword=keyword, status=status, level=level)


@app.get("/api/tickets")
def api_tickets() -> dict:
    return {"items": list_tickets()}


@app.post("/api/chat")
async def api_chat(body: ChatRequest) -> StreamingResponse:
    """Primary chat endpoint: SSE stream of agent steps (live).

    Events: step_start | tool_call | tool_result | final | budget | note | done | error
    """

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
    """Non-stream JSON (scripts / smoke tests). Prefer /api/chat for the UI."""
    try:
        result = await run_agent(
            body.message, body.history, force_timeout=body.force_timeout
        )
    except (LLMConfigError, LLMCallError) as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc
    return ChatResponse(**result)
