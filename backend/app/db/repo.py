"""Domain repository — SQLite/Postgres backed hazards & tickets."""

from __future__ import annotations

from copy import deepcopy
from datetime import date, datetime, timedelta
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from .models import Hazard, Ticket
from .session import SessionLocal

_TODAY = date(2026, 10, 13)
_CLOSED = {"已闭环"}
_ADVANCE = {
    "start": ("待执行", "执行中"),
    "submit_verify": ("执行中", "待验收"),
    "close": ("待验收", "已关闭"),
    "reject": ("待验收", "执行中"),
}


def _parse_date(s: str) -> date | None:
    try:
        return datetime.strptime(s, "%Y-%m-%d").date()
    except Exception:  # noqa: BLE001
        return None


def _h_dict(h: Hazard) -> dict[str, Any]:
    out = {
        "id": h.id,
        "title": h.title,
        "description": h.description,
        "plant": h.plant,
        "area": h.area,
        "category": h.category,
        "level": h.level,
        "status": h.status,
        "discoverer": h.discoverer,
        "discovered_at": h.discovered_at,
        "deadline": h.deadline,
        "owner": h.owner,
        "risk_note": h.risk_note,
    }
    if h.closed_at:
        out["closed_at"] = h.closed_at
    dl = _parse_date(h.deadline)
    closed = h.status in _CLOSED
    overdue = bool(dl and (not closed) and dl < _TODAY)
    out["overdue"] = overdue
    out["display_status"] = "逾期" if overdue and h.status != "逾期" else h.status
    out["location"] = f"{h.plant}·{h.area}"
    out["found_at"] = h.discovered_at
    return out


def _t_dict(t: Ticket) -> dict[str, Any]:
    return {
        "ticket_id": t.ticket_id,
        "hazard_id": t.hazard_id,
        "hazard_title": t.hazard_title,
        "measures": t.measures,
        "action": t.measures,
        "owner": t.owner,
        "assignee": t.owner,
        "due_date": t.due_date,
        "status": t.status,
        "evidence_note": t.evidence_note,
        "created_at": t.created_at,
    }


def with_db(fn):  # noqa: ANN001
    def wrapper(*args, **kwargs):
        db = SessionLocal()
        try:
            return fn(db, *args, **kwargs)
        finally:
            db.close()

    return wrapper


@with_db
def query_hazard_ledger(
    db: Session,
    keyword: str = "",
    status: str = "",
    level: str = "",
    plant: str = "",
    category: str = "",
    overdue_only: bool = False,
) -> dict[str, Any]:
    rows = list(db.scalars(select(Hazard)).all())
    kw = (keyword or "").strip().lower()
    st = (status or "").strip()
    lv = (level or "").strip()
    pl = (plant or "").strip()
    cat = (category or "").strip()
    results = []
    for h in rows:
        item = _h_dict(h)
        blob = " ".join(
            str(item.get(k, ""))
            for k in ("id", "title", "description", "plant", "area", "category", "owner", "risk_note")
        ).lower()
        if kw and kw not in blob:
            continue
        if st:
            if st == "逾期":
                if not item["overdue"]:
                    continue
            elif item["status"] != st:
                continue
        if lv and item["level"] != lv:
            continue
        if pl and pl not in str(item.get("plant", "")):
            continue
        if cat and cat not in str(item.get("category", "")):
            continue
        if overdue_only and not item["overdue"]:
            continue
        results.append(item)
    return {"count": len(results), "as_of": _TODAY.isoformat(), "items": results}


@with_db
def list_open_hazards(db: Session, include_pending_verify: bool = True) -> dict[str, Any]:
    open_statuses = {"待整改", "整改中", "逾期"}
    if include_pending_verify:
        open_statuses.add("待验收")
    items = []
    for h in db.scalars(select(Hazard)).all():
        item = _h_dict(h)
        if item["status"] in _CLOSED:
            continue
        if item["status"] in open_statuses or item["overdue"]:
            items.append(item)
    items.sort(
        key=lambda x: (
            0 if x["level"] == "重大" else 1,
            0 if x["overdue"] else 1,
            x.get("deadline") or "",
            x["id"],
        )
    )
    return {
        "count": len(items),
        "as_of": _TODAY.isoformat(),
        "open_statuses": sorted(open_statuses),
        "items": items,
    }


@with_db
def create_corrective_ticket(
    db: Session,
    hazard_id: str,
    action: str = "",
    measures: str = "",
    assignee: str = "",
    owner: str = "",
    due_days: int = 7,
) -> dict[str, Any]:
    hazard = db.get(Hazard, hazard_id)
    if not hazard:
        return {"ok": False, "error": f"未找到隐患编号 {hazard_id}"}
    if hazard.status in _CLOSED:
        return {"ok": False, "error": f"{hazard_id} 已闭环，不能再开整改单"}
    active = db.scalars(
        select(Ticket).where(Ticket.hazard_id == hazard_id, Ticket.status != "已关闭")
    ).all()
    if active:
        return {
            "ok": False,
            "error": f"{hazard_id} 已有未关闭整改单 {active[0].ticket_id}（{active[0].status}）",
            "existing": _t_dict(active[0]),
        }
    text = (measures or action or "").strip()
    if not text:
        return {"ok": False, "error": "必须提供整改措施 measures/action"}
    who = (owner or assignee or hazard.owner or "待指派").strip()
    due = _TODAY + timedelta(days=int(due_days or 7))
    # next id
    existing_ids = [t.ticket_id for t in db.scalars(select(Ticket)).all()]
    nums = []
    for tid in existing_ids:
        if tid.startswith("CA-"):
            try:
                nums.append(int(tid.split("-", 1)[1]))
            except ValueError:
                pass
    nxt = (max(nums) if nums else 100) + 1
    ticket = Ticket(
        ticket_id=f"CA-{nxt}",
        hazard_id=hazard_id,
        hazard_title=hazard.title,
        measures=text,
        owner=who,
        due_date=due.isoformat(),
        status="待执行",
        evidence_note="",
        created_at=_TODAY.isoformat(),
    )
    db.add(ticket)
    if hazard.status == "待整改":
        hazard.status = "整改中"
    db.commit()
    db.refresh(ticket)
    db.refresh(hazard)
    return {"ok": True, "ticket": _t_dict(ticket), "hazard": _h_dict(hazard)}


@with_db
def list_corrective_tickets(
    db: Session, hazard_id: str = "", status: str = ""
) -> dict[str, Any]:
    q = select(Ticket)
    if hazard_id:
        q = q.where(Ticket.hazard_id == hazard_id.strip())
    if status:
        q = q.where(Ticket.status == status.strip())
    items = [_t_dict(t) for t in db.scalars(q).all()]
    return {"count": len(items), "items": items}


@with_db
def advance_corrective_ticket(
    db: Session, ticket_id: str, action: str, evidence_note: str = ""
) -> dict[str, Any]:
    act = (action or "").strip().lower()
    if act not in _ADVANCE:
        return {"ok": False, "error": f"未知 action={action}，应为 start/submit_verify/close/reject"}
    ticket = db.get(Ticket, ticket_id)
    if not ticket:
        return {"ok": False, "error": f"未找到整改单 {ticket_id}"}
    expect_from, to_status = _ADVANCE[act]
    if ticket.status != expect_from:
        return {
            "ok": False,
            "error": f"{ticket_id} 当前状态为「{ticket.status}」，{act} 仅允许从「{expect_from}」转入「{to_status}」",
        }
    if act == "submit_verify" and evidence_note:
        ticket.evidence_note = evidence_note.strip()
    if act == "close" and not (ticket.evidence_note or evidence_note):
        return {"ok": False, "error": "关闭前须提供验收说明 evidence_note（或先在 submit_verify 写入）"}
    if act == "close" and evidence_note:
        ticket.evidence_note = (
            (ticket.evidence_note or "") + " | 验收：" + evidence_note.strip()
        ).strip(" |")
    ticket.status = to_status
    hazard = db.get(Hazard, ticket.hazard_id)
    if hazard:
        if act == "submit_verify":
            hazard.status = "待验收"
        elif act == "close":
            hazard.status = "已闭环"
            hazard.closed_at = _TODAY.isoformat()
        elif act == "reject":
            hazard.status = "整改中"
            ticket.evidence_note = (
                (ticket.evidence_note or "") + " | 驳回：" + (evidence_note or "验收不通过")
            ).strip(" |")
        elif act == "start" and hazard.status == "待整改":
            hazard.status = "整改中"
    db.commit()
    db.refresh(ticket)
    if hazard:
        db.refresh(hazard)
    return {
        "ok": True,
        "ticket": _t_dict(ticket),
        "hazard": _h_dict(hazard) if hazard else None,
        "transition": {"action": act, "from": expect_from, "to": to_status},
    }


@with_db
def list_tickets(db: Session) -> list[dict[str, Any]]:
    return [_t_dict(t) for t in db.scalars(select(Ticket)).all()]
