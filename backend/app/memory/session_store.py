"""Persist chat session message history (Ch10)."""

from __future__ import annotations

import json
from typing import Any
from uuid import uuid4

from sqlalchemy.orm import Session

from app.db import models


class SessionStore:
    def __init__(self, db: Session):
        self.db = db

    def get_or_create(
        self,
        *,
        tenant_id: str,
        session_id: str | None = None,
        actor: str = "",
    ) -> models.AgentSession:
        if session_id:
            row = (
                self.db.query(models.AgentSession)
                .filter(
                    models.AgentSession.session_id == session_id,
                    models.AgentSession.tenant_id == tenant_id,
                )
                .one_or_none()
            )
            if row:
                return row
        sid = session_id or f"ses_{uuid4().hex[:12]}"
        row = models.AgentSession(
            session_id=sid,
            tenant_id=tenant_id,
            actor=actor or "",
            messages_json="[]",
            summary="",
        )
        self.db.add(row)
        self.db.commit()
        self.db.refresh(row)
        return row

    def load_messages(self, row: models.AgentSession) -> list[dict[str, Any]]:
        try:
            data = json.loads(row.messages_json or "[]")
            return data if isinstance(data, list) else []
        except json.JSONDecodeError:
            return []

    def append_turn(
        self,
        row: models.AgentSession,
        *,
        user: str,
        assistant: str,
        meta: dict[str, Any] | None = None,
    ) -> list[dict[str, Any]]:
        msgs = self.load_messages(row)
        msgs.append({"role": "user", "content": user})
        msgs.append({"role": "assistant", "content": assistant})
        if meta and meta.get("compressed"):
            row.summary = str(meta.get("summary_preview") or row.summary or "")
        row.messages_json = json.dumps(msgs, ensure_ascii=False)
        self.db.add(row)
        self.db.commit()
        self.db.refresh(row)
        return msgs
