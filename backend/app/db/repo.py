from __future__ import annotations

import json
from datetime import date, datetime, timedelta, timezone
from typing import Any

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.db.models import AuditEvent, Hazard, Ticket
from app.domain.capa import hazard_status_for_action, require_evidence_for_close, transition


def append_audit(
    session: Session,
    *,
    tenant_id: str,
    role: str,
    actor: str,
    action: str,
    target_type: str,
    target_id: str,
    payload: dict[str, Any] | None = None,
    ok: bool = True,
    error: str | None = None,
) -> AuditEvent:
    event = AuditEvent(
        tenant_id=tenant_id,
        role=role,
        actor=actor,
        action=action,
        target_type=target_type,
        target_id=target_id,
        payload_json=json.dumps(payload or {}, ensure_ascii=False),
        ok=ok,
        error=error,
    )
    session.add(event)
    session.flush()
    return event


def list_hazards(
    session: Session,
    tenant_id: str,
    *,
    status: str | None = None,
    level: str | None = None,
    plant: str | None = None,
    keyword: str | None = None,
) -> list[Hazard]:
    q = select(Hazard).where(Hazard.tenant_id == tenant_id)
    if status:
        q = q.where(Hazard.status == status)
    if level:
        q = q.where(Hazard.level == level)
    if plant:
        q = q.where(Hazard.plant == plant)
    if keyword:
        like = f"%{keyword}%"
        q = q.where(Hazard.title.like(like) | Hazard.description.like(like))
    q = q.order_by(Hazard.id)
    return list(session.scalars(q).all())


def get_hazard(session: Session, tenant_id: str, hazard_id: str) -> Hazard | None:
    return session.scalar(
        select(Hazard).where(Hazard.id == hazard_id, Hazard.tenant_id == tenant_id)
    )


def list_tickets(
    session: Session,
    tenant_id: str,
    *,
    hazard_id: str | None = None,
    status: str | None = None,
) -> list[Ticket]:
    q = select(Ticket).where(Ticket.tenant_id == tenant_id)
    if hazard_id:
        q = q.where(Ticket.hazard_id == hazard_id)
    if status:
        q = q.where(Ticket.status == status)
    q = q.order_by(Ticket.ticket_id)
    return list(session.scalars(q).all())


def get_ticket(session: Session, tenant_id: str, ticket_id: str) -> Ticket | None:
    return session.scalar(
        select(Ticket).where(Ticket.ticket_id == ticket_id, Ticket.tenant_id == tenant_id)
    )


def _next_ticket_id(session: Session) -> str:
    count = session.scalar(select(func.count()).select_from(Ticket)) or 0
    return f"TK-{2026}-{count + 1:03d}"


def create_ticket(
    session: Session,
    *,
    tenant_id: str,
    role: str,
    actor: str,
    hazard_id: str,
    measures: str,
    owner: str | None = None,
    due_days: int | None = 7,
) -> tuple[Ticket | None, str | None]:
    hazard = get_hazard(session, tenant_id, hazard_id)
    if hazard is None:
        # Could be missing or wrong tenant — treat as not found for caller
        append_audit(
            session,
            tenant_id=tenant_id,
            role=role,
            actor=actor,
            action="ticket.create",
            target_type="hazard",
            target_id=hazard_id,
            payload={"measures": (measures or "")[:200]},
            ok=False,
            error="隐患不存在或不属于当前租户",
        )
        session.commit()
        return None, "隐患不存在或不属于当前租户"

    open_tickets = list_tickets(session, tenant_id, hazard_id=hazard_id)
    if any(t.status != "已关闭" for t in open_tickets):
        msg = "该隐患已有未关闭整改单"
        append_audit(
            session,
            tenant_id=tenant_id,
            role=role,
            actor=actor,
            action="ticket.create",
            target_type="hazard",
            target_id=hazard_id,
            payload={"measures": (measures or "")[:200]},
            ok=False,
            error=msg,
        )
        session.commit()
        return None, msg

    if not (measures or "").strip():
        msg = "整改措施 measures 不能为空"
        append_audit(
            session,
            tenant_id=tenant_id,
            role=role,
            actor=actor,
            action="ticket.create",
            target_type="hazard",
            target_id=hazard_id,
            ok=False,
            error=msg,
        )
        session.commit()
        return None, msg

    ticket = Ticket(
        ticket_id=_next_ticket_id(session),
        hazard_id=hazard_id,
        tenant_id=tenant_id,
        measures=measures.strip(),
        owner=(owner or hazard.owner or actor).strip(),
        due_date=date.today() + timedelta(days=due_days or 7),
        status="待执行",
    )
    session.add(ticket)
    hazard.status = "整改中"
    append_audit(
        session,
        tenant_id=tenant_id,
        role=role,
        actor=actor,
        action="ticket.create",
        target_type="ticket",
        target_id=ticket.ticket_id,
        payload={
            "hazard_id": hazard_id,
            "measures": measures.strip()[:200],
            "from": None,
            "to": "待执行",
        },
        ok=True,
    )
    session.commit()
    session.refresh(ticket)
    return ticket, None


def advance_ticket(
    session: Session,
    *,
    tenant_id: str,
    role: str,
    actor: str,
    ticket_id: str,
    action: str,
    evidence_note: str | None = None,
) -> tuple[Ticket | None, str | None, int]:
    """Returns (ticket, error, http_hint). http_hint is 400/404."""
    ticket = get_ticket(session, tenant_id, ticket_id)
    if ticket is None:
        append_audit(
            session,
            tenant_id=tenant_id,
            role=role,
            actor=actor,
            action="ticket.denied",
            target_type="ticket",
            target_id=ticket_id,
            payload={"attempted_action": action},
            ok=False,
            error="整改单不存在或不属于当前租户",
        )
        session.commit()
        return None, "整改单不存在或不属于当前租户", 404

    evidence_err = require_evidence_for_close(action, evidence_note)
    if evidence_err:
        append_audit(
            session,
            tenant_id=tenant_id,
            role=role,
            actor=actor,
            action="ticket.denied",
            target_type="ticket",
            target_id=ticket_id,
            payload={
                "attempted_action": action,
                "from": ticket.status,
                "evidence_provided": False,
            },
            ok=False,
            error=evidence_err,
        )
        session.commit()
        return ticket, evidence_err, 400

    new_status, err = transition(ticket.status, action)
    if err:
        append_audit(
            session,
            tenant_id=tenant_id,
            role=role,
            actor=actor,
            action="ticket.denied",
            target_type="ticket",
            target_id=ticket_id,
            payload={"attempted_action": action, "from": ticket.status},
            ok=False,
            error=err,
        )
        session.commit()
        return ticket, err, 400

    old_status = ticket.status
    ticket.status = new_status
    if action == "close":
        ticket.evidence_note = (evidence_note or "").strip()
    elif evidence_note and str(evidence_note).strip():
        # allow draft evidence on submit_verify
        ticket.evidence_note = str(evidence_note).strip()

    hazard = get_hazard(session, tenant_id, ticket.hazard_id)
    hz_status = hazard_status_for_action(action)
    if hazard and hz_status:
        hazard.status = hz_status
        if action == "close":
            hazard.closed_at = datetime.now(timezone.utc)

    append_audit(
        session,
        tenant_id=tenant_id,
        role=role,
        actor=actor,
        action="ticket.advance",
        target_type="ticket",
        target_id=ticket_id,
        payload={
            "attempted_action": action,
            "from": old_status,
            "to": new_status,
            "evidence_provided": bool(evidence_note and str(evidence_note).strip()),
        },
        ok=True,
    )
    session.commit()
    session.refresh(ticket)
    return ticket, None, 200


def list_audit(
    session: Session,
    tenant_id: str,
    *,
    limit: int = 50,
    action: str | None = None,
) -> list[AuditEvent]:
    q = select(AuditEvent).where(AuditEvent.tenant_id == tenant_id)
    if action:
        q = q.where(AuditEvent.action == action)
    q = q.order_by(AuditEvent.id.desc()).limit(limit)
    return list(session.scalars(q).all())
