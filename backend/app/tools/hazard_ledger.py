"""Mock EHS hazard ledger — in-memory demo data."""

from __future__ import annotations

from copy import deepcopy
from typing import Any

_HAZARDS: list[dict[str, Any]] = [
    {
        "id": "HZ-2026-001",
        "title": "车间西侧灭火器过期",
        "location": "一号车间西侧通道",
        "level": "一般",
        "status": "待整改",
        "owner": "张三",
        "found_at": "2026-10-01",
        "deadline": "2026-10-15",
    },
    {
        "id": "HZ-2026-002",
        "title": "配电柜未上锁",
        "location": "配电房 A",
        "level": "重大",
        "status": "整改中",
        "owner": "李四",
        "found_at": "2026-10-05",
        "deadline": "2026-10-08",
    },
    {
        "id": "HZ-2026-003",
        "title": "安全通道堆放纸箱",
        "location": "二号仓库北门",
        "level": "一般",
        "status": "已闭环",
        "owner": "王五",
        "found_at": "2026-09-20",
        "deadline": "2026-09-27",
    },
]

_TICKETS: list[dict[str, Any]] = []
_ticket_seq = 100


def query_hazard_ledger(keyword: str = "", status: str = "", level: str = "") -> dict[str, Any]:
    """Search mock hazards by keyword / status / level."""
    kw = (keyword or "").strip().lower()
    st = (status or "").strip()
    lv = (level or "").strip()
    results = []
    for h in _HAZARDS:
        if kw and kw not in h["title"].lower() and kw not in h["location"].lower() and kw not in h["id"].lower():
            continue
        if st and h["status"] != st:
            continue
        if lv and h["level"] != lv:
            continue
        results.append(deepcopy(h))
    return {"count": len(results), "items": results}


def create_corrective_ticket(
    hazard_id: str,
    action: str,
    assignee: str = "待指派",
    due_days: int = 7,
) -> dict[str, Any]:
    """Create a mock corrective-action ticket linked to a hazard."""
    global _ticket_seq
    hazard = next((h for h in _HAZARDS if h["id"] == hazard_id), None)
    if not hazard:
        return {"ok": False, "error": f"未找到隐患编号 {hazard_id}"}
    _ticket_seq += 1
    ticket = {
        "ticket_id": f"CA-{_ticket_seq}",
        "hazard_id": hazard_id,
        "hazard_title": hazard["title"],
        "action": action,
        "assignee": assignee,
        "due_days": due_days,
        "status": "已开单",
    }
    _TICKETS.append(ticket)
    if hazard["status"] == "待整改":
        hazard["status"] = "整改中"
    return {"ok": True, "ticket": deepcopy(ticket)}


def list_open_hazards() -> dict[str, Any]:
    """List all hazards that are still open (待整改 or 整改中)."""
    open_statuses = {"待整改", "整改中"}
    items = [deepcopy(h) for h in _HAZARDS if h["status"] in open_statuses]
    # 待整改 first, then 整改中; within same status keep original order
    items.sort(key=lambda h: (0 if h["status"] == "待整改" else 1, h["id"]))
    return {
        "count": len(items),
        "open_statuses": sorted(open_statuses),
        "items": items,
    }


def list_tickets() -> list[dict[str, Any]]:
    return deepcopy(_TICKETS)
