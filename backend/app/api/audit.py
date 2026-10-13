from __future__ import annotations

import json
from datetime import datetime
from typing import Annotated, Any

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.auth.deps import Identity
from app.db import repo
from app.db.session import get_db

router = APIRouter(prefix="/api", tags=["audit"])


class AuditOut(BaseModel):
    id: int
    ts: datetime | None
    tenant_id: str
    role: str
    actor: str
    action: str
    target_type: str
    target_id: str
    payload: dict[str, Any]
    ok: bool
    error: str | None


@router.get("/audit", response_model=list[AuditOut])
def get_audit(
    identity: Identity,
    db: Annotated[Session, Depends(get_db)],
    limit: int = Query(50, ge=1, le=200),
    action: str | None = None,
):
    if identity["role"] == "viewer":
        raise HTTPException(status_code=403, detail="viewer 无权查看审计")
    rows = repo.list_audit(
        db, identity["tenant_id"], limit=limit, action=action
    )
    out: list[AuditOut] = []
    for r in rows:
        try:
            payload = json.loads(r.payload_json or "{}")
        except json.JSONDecodeError:
            payload = {}
        out.append(
            AuditOut(
                id=r.id,
                ts=r.ts,
                tenant_id=r.tenant_id,
                role=r.role,
                actor=r.actor,
                action=r.action,
                target_type=r.target_type,
                target_id=r.target_id,
                payload=payload,
                ok=r.ok,
                error=r.error,
            )
        )
    return out
