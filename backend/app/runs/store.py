"""Durable agent run store — checkpoint JSON in DB (Ch4)."""

from __future__ import annotations

import json
from datetime import datetime, timezone
from typing import Any
from uuid import uuid4

from sqlalchemy import select

from app.db.models import AgentRun
from app.db import session as db_session


def _loads(s: str, default: Any) -> Any:
    try:
        return json.loads(s or "") if s else default
    except json.JSONDecodeError:
        return default


def _row(r: AgentRun) -> dict[str, Any]:
    return {
        "run_id": r.run_id,
        "tenant_id": r.tenant_id,
        "role": r.role,
        "status": r.status,
        "message": r.message,
        "reply": r.reply,
        "error": r.error,
        "checkpoint": _loads(r.checkpoint_json, {}),
        "steps": _loads(r.steps_json, []),
        "budget_used": r.budget_used,
        "budget_max": r.budget_max,
        "session_id": r.session_id,
        "created_at": r.created_at.isoformat() if r.created_at else None,
        "updated_at": r.updated_at.isoformat() if r.updated_at else None,
    }


class RunsStore:
    def create(
        self,
        *,
        message: str,
        tenant_id: str = "demo-plant",
        role: str = "ehs_engineer",
        session_id: str | None = None,
        budget_max: int = 8,
        history: list[dict] | None = None,
    ) -> dict[str, Any]:
        run_id = f"run_{uuid4().hex[:12]}"
        ck = {
            "message": message,
            "history": list(history or []),
            "tool_results": [],
            "steps": [],
            "budget_used": 0,
            "next_index": 0,
        }
        now = datetime.now(timezone.utc)
        db = db_session.SessionLocal()
        try:
            row = AgentRun(
                run_id=run_id,
                tenant_id=tenant_id,
                role=role,
                status="pending",
                message=message,
                reply="",
                error="",
                checkpoint_json=json.dumps(ck, ensure_ascii=False),
                steps_json="[]",
                budget_used=0,
                budget_max=budget_max,
                session_id=session_id,
                created_at=now,
                updated_at=now,
            )
            db.add(row)
            db.commit()
            db.refresh(row)
            return _row(row)
        finally:
            db.close()

    def get(self, run_id: str) -> dict[str, Any] | None:
        db = db_session.SessionLocal()
        try:
            row = db.get(AgentRun, run_id)
            return _row(row) if row else None
        finally:
            db.close()

    def list(self, *, tenant_id: str | None = None, limit: int = 50) -> list[dict[str, Any]]:
        db = db_session.SessionLocal()
        try:
            q = select(AgentRun).order_by(AgentRun.created_at.desc()).limit(limit)
            if tenant_id:
                q = q.where(AgentRun.tenant_id == tenant_id)
            return [_row(r) for r in db.scalars(q).all()]
        finally:
            db.close()

    def save_checkpoint(
        self,
        run_id: str,
        *,
        status: str,
        checkpoint: dict[str, Any],
        steps: list[dict[str, Any]],
        budget_used: int,
        reply: str = "",
        error: str = "",
    ) -> dict[str, Any] | None:
        db = db_session.SessionLocal()
        try:
            row = db.get(AgentRun, run_id)
            if not row:
                return None
            row.status = status
            row.checkpoint_json = json.dumps(checkpoint, ensure_ascii=False)
            row.steps_json = json.dumps(steps, ensure_ascii=False)
            row.budget_used = budget_used
            if reply:
                row.reply = reply
            if error:
                row.error = error
            row.updated_at = datetime.now(timezone.utc)
            db.commit()
            db.refresh(row)
            return _row(row)
        finally:
            db.close()


runs = RunsStore()
