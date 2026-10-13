"""Domain tools: always call app.db.repo so CAPA + ACL audit paths stay intact."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from sqlalchemy.orm import Session

from app.auth.tenant import domain_can_write
from app.db import repo


@dataclass
class ToolContext:
    session: Session
    tenant_id: str
    role: str
    actor: str


def _hazard_dict(h) -> dict[str, Any]:
    return {
        "id": h.id,
        "title": h.title,
        "description": h.description,
        "plant": h.plant,
        "area": h.area,
        "category": h.category,
        "level": h.level,
        "status": h.status,
        "owner": h.owner,
        "deadline": h.deadline.isoformat() if h.deadline else None,
        "risk_note": h.risk_note,
    }


def _ticket_dict(t) -> dict[str, Any]:
    return {
        "ticket_id": t.ticket_id,
        "hazard_id": t.hazard_id,
        "measures": t.measures,
        "owner": t.owner,
        "due_date": t.due_date.isoformat() if t.due_date else None,
        "status": t.status,
        "evidence_note": t.evidence_note,
    }


def _deny_write(ctx: ToolContext, *, action: str, target_type: str, target_id: str) -> dict[str, Any]:
    msg = "当前角色只读，禁止写操作"
    repo.append_audit(
        ctx.session,
        tenant_id=ctx.tenant_id,
        role=ctx.role,
        actor=ctx.actor,
        action="ticket.denied",
        target_type=target_type,
        target_id=target_id,
        payload={"attempted_action": action, "via": "agent_tool"},
        ok=False,
        error=msg,
    )
    ctx.session.commit()
    return {"ok": False, "error": msg, "denied": True}


def query_hazard_ledger(
    ctx: ToolContext,
    keyword: str = "",
    status: str = "",
    level: str = "",
    plant: str = "",
    **_extra: Any,
) -> dict[str, Any]:
    rows = repo.list_hazards(
        ctx.session,
        ctx.tenant_id,
        status=status or None,
        level=level or None,
        plant=plant or None,
        keyword=keyword or None,
    )
    items = [_hazard_dict(h) for h in rows]
    return {"ok": True, "result": {"items": items, "count": len(items)}}


def list_open_hazards(ctx: ToolContext, **_extra: Any) -> dict[str, Any]:
    rows = repo.list_hazards(ctx.session, ctx.tenant_id)
    open_status = {"待整改", "整改中"}
    items = [_hazard_dict(h) for h in rows if h.status in open_status]
    # major first
    items.sort(key=lambda x: (0 if x["level"] == "重大" else 1, x["id"]))
    return {"ok": True, "result": {"items": items, "count": len(items)}}


def list_corrective_tickets(
    ctx: ToolContext, hazard_id: str = "", status: str = "", **_extra: Any
) -> dict[str, Any]:
    rows = repo.list_tickets(
        ctx.session,
        ctx.tenant_id,
        hazard_id=hazard_id or None,
        status=status or None,
    )
    items = [_ticket_dict(t) for t in rows]
    return {"ok": True, "result": {"items": items, "count": len(items)}}


def create_corrective_ticket(
    ctx: ToolContext,
    hazard_id: str,
    action: str = "",
    measures: str = "",
    assignee: str = "",
    owner: str = "",
    due_days: int = 7,
    **_extra: Any,
) -> dict[str, Any]:
    if not domain_can_write(ctx.role):
        return _deny_write(ctx, action="ticket.create", target_type="hazard", target_id=hazard_id)
    text = (measures or action or "").strip()
    ticket, err = repo.create_ticket(
        ctx.session,
        tenant_id=ctx.tenant_id,
        role=ctx.role,
        actor=ctx.actor,
        hazard_id=hazard_id,
        measures=text or "按制度完成整改并复查",
        owner=owner or assignee or None,
        due_days=due_days or 7,
    )
    if err:
        return {"ok": False, "error": err}
    return {"ok": True, "ticket": _ticket_dict(ticket)}


def advance_corrective_ticket(
    ctx: ToolContext,
    ticket_id: str,
    action: str,
    evidence_note: str = "",
    **_extra: Any,
) -> dict[str, Any]:
    if not domain_can_write(ctx.role):
        return _deny_write(ctx, action=action, target_type="ticket", target_id=ticket_id)
    ticket, err, _code = repo.advance_ticket(
        ctx.session,
        tenant_id=ctx.tenant_id,
        role=ctx.role,
        actor=ctx.actor,
        ticket_id=ticket_id,
        action=action,
        evidence_note=evidence_note or None,
    )
    if err:
        return {"ok": False, "error": err, "ticket": _ticket_dict(ticket) if ticket else None}
    hazard = repo.get_hazard(ctx.session, ctx.tenant_id, ticket.hazard_id) if ticket else None
    return {
        "ok": True,
        "ticket": _ticket_dict(ticket),
        "hazard": {"status": hazard.status} if hazard else None,
    }


def search_regulations(
    ctx: ToolContext,
    query: str = "",
    top_k: int = 3,
    **_extra: Any,
) -> dict[str, Any]:
    """Retrieve EHS regulation chunks (local embedding RAG). Read-only."""
    from app.rag.store import get_regulations_store

    q = (query or "").strip()
    if not q:
        return {"ok": False, "error": "query 不能为空"}
    store = get_regulations_store()
    hits = store.search(q, top_k=int(top_k or 3))
    return {
        "ok": True,
        "result": {
            "query": q,
            "hits": hits,
            "count": len(hits),
        },
    }
