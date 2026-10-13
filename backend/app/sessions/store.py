"""Chapter 7 + eng-1: chat sessions persisted in SQLAlchemy DB."""

from __future__ import annotations

from copy import deepcopy
from datetime import datetime
from typing import Any
from uuid import uuid4

from sqlalchemy import select
from sqlalchemy.orm import selectinload

from ..db.models import ChatMessage, ChatSession
from ..db.session import SessionLocal


class SessionStore:
    def create(self, tenant_id: str = "default", role: str = "ehs_engineer") -> dict[str, Any]:
        sid = f"ses_{uuid4().hex[:12]}"
        db = SessionLocal()
        try:
            rec = ChatSession(session_id=sid, tenant_id=tenant_id, role=role, turns=0)
            db.add(rec)
            db.commit()
            return {
                "session_id": sid,
                "tenant_id": tenant_id,
                "role": role,
                "history": [],
                "turns": 0,
            }
        finally:
            db.close()

    def get(self, session_id: str) -> dict[str, Any] | None:
        db = SessionLocal()
        try:
            rec = db.scalars(
                select(ChatSession)
                .where(ChatSession.session_id == session_id)
                .options(selectinload(ChatSession.messages))
            ).first()
            if not rec:
                return None
            history = [{"role": m.role, "content": m.content} for m in rec.messages]
            return {
                "session_id": rec.session_id,
                "tenant_id": rec.tenant_id,
                "role": rec.role,
                "history": history,
                "turns": rec.turns,
            }
        finally:
            db.close()

    def append_turn(self, session_id: str, user: str, assistant: str) -> dict[str, Any]:
        db = SessionLocal()
        try:
            rec = db.scalars(
                select(ChatSession)
                .where(ChatSession.session_id == session_id)
                .options(selectinload(ChatSession.messages))
            ).first()
            if not rec:
                raise KeyError(session_id)
            seq = len(rec.messages)
            db.add(ChatMessage(session_id=session_id, seq=seq, role="user", content=user))
            db.add(
                ChatMessage(session_id=session_id, seq=seq + 1, role="assistant", content=assistant)
            )
            rec.turns += 1
            rec.updated_at = datetime.utcnow()
            # trim older than 20 messages
            db.flush()
            msgs = list(
                db.scalars(
                    select(ChatMessage)
                    .where(ChatMessage.session_id == session_id)
                    .order_by(ChatMessage.seq)
                ).all()
            )
            if len(msgs) > 20:
                for m in msgs[:-20]:
                    db.delete(m)
            db.commit()
            return self.get(session_id) or {}
        finally:
            db.close()

    def history(self, session_id: str) -> list[dict[str, str]]:
        rec = self.get(session_id)
        if not rec:
            return []
        return list(rec.get("history") or [])


sessions = SessionStore()
