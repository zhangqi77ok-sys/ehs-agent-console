"""HITL approval records (Ch5)."""

from __future__ import annotations

import json
from datetime import datetime, timezone
from typing import Any
from uuid import uuid4

from sqlalchemy import select

from app.db.models import AgentApproval
from app.db import session as db_session


def _row(a: AgentApproval) -> dict[str, Any]:
    return {
        "approval_id": a.approval_id,
        "run_id": a.run_id,
        "tool_name": a.tool_name,
        "arguments": json.loads(a.arguments_json or "{}"),
        "call_id": a.call_id,
        "status": a.status,
        "decided_by": a.decided_by,
        "note": a.note,
        "created_at": a.created_at.isoformat() if a.created_at else None,
        "decided_at": a.decided_at.isoformat() if a.decided_at else None,
    }


def create_approval(
    *,
    run_id: str,
    tool_name: str,
    arguments: dict[str, Any],
    call_id: str,
) -> dict[str, Any]:
    db = db_session.SessionLocal()
    try:
        row = AgentApproval(
            approval_id=f"ap_{uuid4().hex[:12]}",
            run_id=run_id,
            tool_name=tool_name,
            arguments_json=json.dumps(arguments or {}, ensure_ascii=False),
            call_id=call_id or "",
            status="pending",
            decided_by="",
            note="",
            created_at=datetime.now(timezone.utc),
            decided_at=None,
        )
        db.add(row)
        db.commit()
        db.refresh(row)
        return _row(row)
    finally:
        db.close()


def get_approval(approval_id: str) -> dict[str, Any] | None:
    db = db_session.SessionLocal()
    try:
        row = db.get(AgentApproval, approval_id)
        return _row(row) if row else None
    finally:
        db.close()


def list_approvals(
    *, run_id: str | None = None, status: str | None = "pending", limit: int = 50
) -> list[dict[str, Any]]:
    db = db_session.SessionLocal()
    try:
        q = select(AgentApproval).order_by(AgentApproval.created_at.desc()).limit(limit)
        if run_id:
            q = q.where(AgentApproval.run_id == run_id)
        if status:
            q = q.where(AgentApproval.status == status)
        return [_row(r) for r in db.scalars(q).all()]
    finally:
        db.close()


def decide_approval(
    approval_id: str, *, approve: bool, decided_by: str = "", note: str = ""
) -> dict[str, Any] | None:
    db = db_session.SessionLocal()
    try:
        row = db.get(AgentApproval, approval_id)
        if not row:
            return None
        if row.status != "pending":
            return _row(row)
        row.status = "approved" if approve else "rejected"
        row.decided_by = decided_by or "operator"
        row.note = note or ""
        row.decided_at = datetime.now(timezone.utc)
        db.commit()
        db.refresh(row)
        return _row(row)
    finally:
        db.close()
