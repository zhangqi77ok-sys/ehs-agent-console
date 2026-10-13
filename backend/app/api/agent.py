"""Ch2/Ch3: agent chat (JSON) + SSE stream."""

from __future__ import annotations

import json
from typing import Annotated, Any, AsyncIterator

from fastapi import APIRouter, Depends
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.agent.loop import run_agent, stream_agent
from app.auth.deps import Identity
from app.db.session import get_db

router = APIRouter(prefix="/api/agent", tags=["agent"])


class ChatBody(BaseModel):
    message: str = Field(..., min_length=1)
    history: list[dict[str, Any]] = Field(default_factory=list)
    force_timeout: bool = False
    pause_after_steps: int | None = Field(default=None, ge=1)
    stream: bool = False


def _sse(event: str, data: dict[str, Any]) -> str:
    return f"event: {event}\ndata: {json.dumps(data, ensure_ascii=False)}\n\n"


@router.post("/chat")
async def agent_chat(
    body: ChatBody,
    identity: Identity,
    db: Annotated[Session, Depends(get_db)],
):
    """JSON agent turn (Ch2). Set stream=true or use /chat/stream for SSE (Ch3)."""
    if body.stream:
        return await _stream_response(body, identity, db)

    result = await run_agent(
        body.message,
        db,
        history=body.history,
        force_timeout=body.force_timeout,
        tenant_id=identity["tenant_id"],
        role=identity["role"],
        actor=identity["actor"],
        pause_after_steps=body.pause_after_steps,
        hitl_enabled=False,  # Ch2/3/4 JSON path: HITL via /api/runs (Ch5)
    )
    return result


@router.post("/chat/stream")
async def agent_chat_stream(
    body: ChatBody,
    identity: Identity,
    db: Annotated[Session, Depends(get_db)],
):
    return await _stream_response(body, identity, db)


async def _stream_response(body: ChatBody, identity: dict, db: Session) -> StreamingResponse:
    async def gen() -> AsyncIterator[str]:
        async for evt in stream_agent(
            body.message,
            db,
            history=body.history,
            force_timeout=body.force_timeout,
            tenant_id=identity["tenant_id"],
            role=identity["role"],
            actor=identity["actor"],
            pause_after_steps=body.pause_after_steps,
            hitl_enabled=False,
        ):
            yield _sse(evt["event"], evt["data"])

    return StreamingResponse(gen(), media_type="text/event-stream")
