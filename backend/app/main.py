"""EHS Agent Console API."""

from __future__ import annotations

import json
from typing import Any

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field

from .agent.loop import run_agent, stream_agent
from .config import settings
from .tools.hazard_ledger import list_tickets, query_hazard_ledger

app = FastAPI(title="EHS Agent Console", version="0.1.0")

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


class ChatResponse(BaseModel):
    reply: str
    steps: list[dict[str, Any]]
    budget: dict[str, Any]


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok", "llm_provider": settings.llm_provider}


@app.get("/api/hazards")
def api_hazards(keyword: str = "", status: str = "", level: str = "") -> dict:
    return query_hazard_ledger(keyword=keyword, status=status, level=level)


@app.get("/api/tickets")
def api_tickets() -> dict:
    return {"items": list_tickets()}


@app.post("/api/chat", response_model=ChatResponse)
async def api_chat(body: ChatRequest) -> ChatResponse:
    result = await run_agent(body.message, body.history)
    return ChatResponse(**result)


@app.post("/api/chat/stream")
async def api_chat_stream(body: ChatRequest) -> StreamingResponse:
    async def event_gen():
        async for evt in stream_agent(body.message, body.history):
            yield f"event: {evt['event']}\ndata: {json.dumps(evt['data'], ensure_ascii=False)}\n\n"

    return StreamingResponse(event_gen(), media_type="text/event-stream")
