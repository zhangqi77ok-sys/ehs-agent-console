"""Ch2/Ch3/Ch10: agent chat (JSON) + SSE stream + session memory."""

from __future__ import annotations

import json
from typing import Annotated, Any, AsyncIterator

from fastapi import APIRouter, Depends
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.agent.loop import run_agent, stream_agent
from app.agent.supervisor import run_supervised, stream_supervised
from app.auth.deps import Identity
import app.config as config_mod
from app.db.session import get_db
from app.memory.compress import compress_history
from app.memory.session_store import SessionStore

router = APIRouter(prefix="/api/agent", tags=["agent"])


class ChatBody(BaseModel):
    message: str = Field(..., min_length=1)
    history: list[dict[str, Any]] = Field(default_factory=list)
    session_id: str | None = None
    force_timeout: bool = False
    pause_after_steps: int | None = Field(default=None, ge=1)
    stream: bool = False
    multi_agent: bool = False


def _sse(event: str, data: dict[str, Any]) -> str:
    return f"event: {event}\ndata: {json.dumps(data, ensure_ascii=False)}\n\n"


def _prepare_history(
    body: ChatBody,
    identity: dict,
    db: Session,
) -> tuple[list[dict[str, Any]], dict[str, Any], str | None]:
    store = SessionStore(db)
    hist = list(body.history or [])
    # Always bind a session so multi-turn memory works; client may pass session_id to continue.
    row = store.get_or_create(
        tenant_id=identity["tenant_id"],
        session_id=body.session_id,
        actor=identity.get("actor") or "",
    )
    session_id = row.session_id
    stored = store.load_messages(row)
    if stored:
        hist = stored + hist
    compressed, meta = compress_history(
        hist,
        max_chars=config_mod.settings.memory_max_chars,
        keep_recent=config_mod.settings.memory_keep_recent,
    )
    return compressed, meta, session_id


def _persist_turn(
    db: Session,
    identity: dict,
    session_id: str | None,
    message: str,
    reply: str,
    meta: dict[str, Any],
) -> str | None:
    if not session_id:
        return None
    store = SessionStore(db)
    row = store.get_or_create(
        tenant_id=identity["tenant_id"],
        session_id=session_id,
        actor=identity.get("actor") or "",
    )
    store.append_turn(row, user=message, assistant=reply, meta=meta)
    return row.session_id


@router.post("/chat")
async def agent_chat(
    body: ChatBody,
    identity: Identity,
    db: Annotated[Session, Depends(get_db)],
):
    """JSON agent turn (Ch2). Set stream=true or use /chat/stream for SSE (Ch3)."""
    if body.stream:
        return await _stream_response(body, identity, db)

    history, memory_meta, session_id = _prepare_history(body, identity, db)
    runner = run_supervised if body.multi_agent else run_agent
    result = await runner(
        body.message,
        db,
        history=history,
        force_timeout=body.force_timeout,
        tenant_id=identity["tenant_id"],
        role=identity["role"],
        actor=identity["actor"],
        pause_after_steps=body.pause_after_steps,
        hitl_enabled=False,  # Ch2/3/4 JSON path: HITL via /api/runs (Ch5)
    )
    sid = _persist_turn(
        db, identity, session_id, body.message, result.get("reply") or "", memory_meta
    )
    result["memory"] = memory_meta
    if sid:
        result["session_id"] = sid
    return result


@router.post("/chat/stream")
async def agent_chat_stream(
    body: ChatBody,
    identity: Identity,
    db: Annotated[Session, Depends(get_db)],
):
    return await _stream_response(body, identity, db)


async def _stream_response(body: ChatBody, identity: dict, db: Session) -> StreamingResponse:
    history, memory_meta, session_id = _prepare_history(body, identity, db)

    async def gen() -> AsyncIterator[str]:
        yield _sse("memory", {**memory_meta, "session_id": session_id})
        final_reply = ""
        streamer = stream_supervised if body.multi_agent else stream_agent
        async for evt in streamer(
            body.message,
            db,
            history=history,
            force_timeout=body.force_timeout,
            tenant_id=identity["tenant_id"],
            role=identity["role"],
            actor=identity["actor"],
            pause_after_steps=body.pause_after_steps,
            hitl_enabled=False,
        ):
            if evt["event"] == "done":
                final_reply = evt["data"].get("reply") or final_reply
                data = dict(evt["data"])
                data["memory"] = memory_meta
                if session_id:
                    data["session_id"] = session_id
                yield _sse("done", data)
            else:
                yield _sse(evt["event"], evt["data"])
        if session_id:
            _persist_turn(db, identity, session_id, body.message, final_reply, memory_meta)

    return StreamingResponse(gen(), media_type="text/event-stream")
