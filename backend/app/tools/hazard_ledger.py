"""EHS hazard ledger + CAPA — in-memory domain store (interview-demo realism)."""

from __future__ import annotations

from copy import deepcopy
from datetime import date, datetime, timedelta
from typing import Any

# Reference "today" for deterministic overdue demos (Shanghai teaching box).
_TODAY = date(2026, 10, 13)

_OPEN_HAZARD = {"待整改", "整改中", "待验收", "逾期"}
_CLOSED_HAZARD = {"已闭环"}

_HAZARDS: list[dict[str, Any]] = [
    {
        "id": "HZ-2026-001",
        "title": "车间西侧灭火器压力不足/过期",
        "description": "一号车间西侧通道挂墙灭火器指针进入红区，标签显示点检过期。",
        "plant": "一号车间",
        "area": "西侧疏散通道",
        "category": "消防",
        "level": "一般",
        "status": "待整改",
        "discoverer": "巡检员-赵六",
        "discovered_at": "2026-10-01",
        "deadline": "2026-10-15",
        "owner": "张三",
        "risk_note": "初期火灾扑救能力下降，影响疏散通道合规。",
    },
    {
        "id": "HZ-2026-002",
        "title": "配电柜柜门未上锁、无警示标识",
        "description": "配电房 A 低压柜门可随意开启，缺少「有电危险」标识与上锁挂牌。",
        "plant": "动力车间",
        "area": "配电房 A",
        "category": "电气",
        "level": "重大",
        "status": "整改中",
        "discoverer": "EHS-李四",
        "discovered_at": "2026-10-05",
        "deadline": "2026-10-08",
        "owner": "李四",
        "risk_note": "可能发生触电或误操作停电，须立即管控。",
    },
    {
        "id": "HZ-2026-003",
        "title": "安全通道堆放纸箱堵塞",
        "description": "二号仓库北门疏散通道堆放成品纸箱，净宽不足。",
        "plant": "二号仓库",
        "area": "北门疏散通道",
        "category": "消防",
        "level": "一般",
        "status": "已闭环",
        "discoverer": "仓管-王五",
        "discovered_at": "2026-09-20",
        "deadline": "2026-09-27",
        "owner": "王五",
        "risk_note": "火灾时影响疏散；已清运并复核拍照。",
        "closed_at": "2026-09-26",
    },
    {
        "id": "HZ-2026-004",
        "title": "冲压工位防护罩缺失",
        "description": "三号车间 3# 冲床安全防护罩拆卸后未复位，点动试机无连锁。",
        "plant": "三号车间",
        "area": "冲压线 3#",
        "category": "机械",
        "level": "重大",
        "status": "待整改",
        "discoverer": "班长-周七",
        "discovered_at": "2026-10-10",
        "deadline": "2026-10-12",
        "owner": "周七",
        "risk_note": "机械伤害高风险，建议停机挂牌。",
    },
    {
        "id": "HZ-2026-005",
        "title": "危化品暂存间台账与实物不符",
        "description": "危化品库丙酮账面 4 桶、实物 3 桶，领用单缺签字。",
        "plant": "危化品库",
        "area": "暂存间 B",
        "category": "危化",
        "level": "重大",
        "status": "待验收",
        "discoverer": "EHS-钱八",
        "discovered_at": "2026-10-03",
        "deadline": "2026-10-10",
        "owner": "钱八",
        "risk_note": "账实不符可能掩盖泄漏或私自领用。",
    },
    {
        "id": "HZ-2026-006",
        "title": "叉车日检表连续三天空白",
        "description": "物流区 2 号电动叉车班前检查表 10/10–10/12 无记录。",
        "plant": "物流区",
        "area": "叉车停放区",
        "category": "机械",
        "level": "一般",
        "status": "整改中",
        "discoverer": "物流主管-孙九",
        "discovered_at": "2026-10-12",
        "deadline": "2026-10-20",
        "owner": "孙九",
        "risk_note": "未落实班前检查，碰撞/倾覆风险上升。",
    },
    {
        "id": "HZ-2026-007",
        "title": "有限空间作业未办票",
        "description": "污水池清淤当日无有限空间作业票，现场无气体检测记录。",
        "plant": "公用工程",
        "area": "污水池",
        "category": "有限空间",
        "level": "重大",
        "status": "待整改",
        "discoverer": "安全员-吴十",
        "discovered_at": "2026-10-11",
        "deadline": "2026-10-11",
        "owner": "吴十",
        "risk_note": "中毒窒息风险极高，须立即停工补票。",
    },
    {
        "id": "HZ-2026-008",
        "title": "应急照明抽检不亮",
        "description": "办公楼二层疏散指示灯抽检 2/6 不亮。",
        "plant": "办公楼",
        "area": "二层走廊",
        "category": "消防",
        "level": "一般",
        "status": "已闭环",
        "discoverer": "物业-郑一",
        "discovered_at": "2026-09-15",
        "deadline": "2026-09-22",
        "owner": "郑一",
        "risk_note": "已更换灯具并复测。",
        "closed_at": "2026-09-21",
    },
    {
        "id": "HZ-2026-009",
        "title": "气瓶未固定、无防倾倒链",
        "description": "焊接区氧气/乙炔瓶直立但无防倾倒链条，间距不足。",
        "plant": "一号车间",
        "area": "焊接区",
        "category": "危化",
        "level": "一般",
        "status": "待整改",
        "discoverer": "巡检员-赵六",
        "discovered_at": "2026-10-09",
        "deadline": "2026-10-18",
        "owner": "张三",
        "risk_note": "倾倒可能导致阀门损坏与泄漏。",
    },
    {
        "id": "HZ-2026-010",
        "title": "动火作业监护人离岗",
        "description": "机修动火点监护人离开超过 15 分钟，灭火器未放置到位。",
        "plant": "机修车间",
        "area": "管道改造点",
        "category": "动火",
        "level": "重大",
        "status": "整改中",
        "discoverer": "EHS-李四",
        "discovered_at": "2026-10-08",
        "deadline": "2026-10-09",
        "owner": "李四",
        "risk_note": "动火失控风险；已暂停作业待重新交底。",
    },
    {
        "id": "HZ-2026-011",
        "title": "劳保用品发放台账缺项",
        "description": "打磨岗位近两月防护眼镜领用记录缺失。",
        "plant": "三号车间",
        "area": "打磨工位",
        "category": "职业健康",
        "level": "一般",
        "status": "待验收",
        "discoverer": "HR-陈二",
        "discovered_at": "2026-10-06",
        "deadline": "2026-10-16",
        "owner": "陈二",
        "risk_note": "职业伤害防护不足，验收看补发与培训记录。",
    },
    {
        "id": "HZ-2026-012",
        "title": "雨污水混排迹象",
        "description": "厂界雨水井目视有乳化液泡沫，疑似工艺废水混入。",
        "plant": "厂界",
        "area": "东侧雨水井",
        "category": "环保",
        "level": "重大",
        "status": "待整改",
        "discoverer": "环保专员-冯三",
        "discovered_at": "2026-10-12",
        "deadline": "2026-10-14",
        "owner": "冯三",
        "risk_note": "环境违法风险，须溯源封堵并监测。",
    },
]

_TICKETS: list[dict[str, Any]] = [
    {
        "ticket_id": "CA-101",
        "hazard_id": "HZ-2026-002",
        "hazard_title": "配电柜柜门未上锁、无警示标识",
        "measures": "加装挂锁与警示标识，完成上锁挂牌培训",
        "owner": "李四",
        "due_date": "2026-10-08",
        "status": "执行中",
        "evidence_note": "",
        "created_at": "2026-10-05",
    },
    {
        "ticket_id": "CA-102",
        "hazard_id": "HZ-2026-005",
        "hazard_title": "危化品暂存间台账与实物不符",
        "measures": "盘点补录、追查领用单、修订双人双锁制度",
        "owner": "钱八",
        "due_date": "2026-10-10",
        "status": "待验收",
        "evidence_note": "已盘点并补签字，待 EHS 复核",
        "created_at": "2026-10-04",
    },
]
_ticket_seq = 102

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


def _enrich(h: dict[str, Any]) -> dict[str, Any]:
    out = deepcopy(h)
    dl = _parse_date(str(out.get("deadline") or ""))
    closed = out.get("status") in _CLOSED_HAZARD
    overdue = bool(dl and (not closed) and dl < _TODAY)
    out["overdue"] = overdue
    out["display_status"] = "逾期" if overdue and out.get("status") != "逾期" else out.get("status")
    # Expose location alias for older prompts/evals
    out["location"] = f"{out.get('plant', '')}·{out.get('area', '')}"
    out["found_at"] = out.get("discovered_at")
    return out


def _find_hazard(hazard_id: str) -> dict[str, Any] | None:
    return next((h for h in _HAZARDS if h["id"] == hazard_id), None)


def query_hazard_ledger(
    keyword: str = "",
    status: str = "",
    level: str = "",
    plant: str = "",
    category: str = "",
    overdue_only: bool = False,
) -> dict[str, Any]:
    """Search hazards by keyword / status / level / plant / category / overdue."""
    kw = (keyword or "").strip().lower()
    st = (status or "").strip()
    lv = (level or "").strip()
    pl = (plant or "").strip()
    cat = (category or "").strip()
    results = []
    for raw in _HAZARDS:
        h = _enrich(raw)
        blob = " ".join(
            str(h.get(k, ""))
            for k in ("id", "title", "description", "plant", "area", "category", "owner", "risk_note")
        ).lower()
        if kw and kw not in blob:
            continue
        if st:
            if st == "逾期":
                if not h["overdue"]:
                    continue
            elif h["status"] != st:
                continue
        if lv and h["level"] != lv:
            continue
        if pl and pl not in str(h.get("plant", "")):
            continue
        if cat and cat not in str(h.get("category", "")):
            continue
        if overdue_only and not h["overdue"]:
            continue
        results.append(h)
    return {
        "count": len(results),
        "as_of": _TODAY.isoformat(),
        "items": results,
    }


def list_open_hazards(include_pending_verify: bool = True) -> dict[str, Any]:
    """List hazards not yet 已闭环 (optional include 待验收)."""
    open_statuses = {"待整改", "整改中", "逾期"}
    if include_pending_verify:
        open_statuses.add("待验收")
    items = []
    for raw in _HAZARDS:
        h = _enrich(raw)
        if h["status"] in _CLOSED_HAZARD:
            continue
        if h["status"] in open_statuses or h["overdue"]:
            items.append(h)
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


def create_corrective_ticket(
    hazard_id: str,
    action: str = "",
    measures: str = "",
    assignee: str = "",
    owner: str = "",
    due_days: int = 7,
) -> dict[str, Any]:
    """Open a CAPA ticket; refuses closed hazards; one active ticket per hazard."""
    global _ticket_seq
    hazard = _find_hazard(hazard_id)
    if not hazard:
        return {"ok": False, "error": f"未找到隐患编号 {hazard_id}"}
    if hazard["status"] in _CLOSED_HAZARD:
        return {"ok": False, "error": f"{hazard_id} 已闭环，不能再开整改单"}
    active = [
        t
        for t in _TICKETS
        if t["hazard_id"] == hazard_id and t["status"] != "已关闭"
    ]
    if active:
        return {
            "ok": False,
            "error": f"{hazard_id} 已有未关闭整改单 {active[0]['ticket_id']}（{active[0]['status']}）",
            "existing": deepcopy(active[0]),
        }
    text = (measures or action or "").strip()
    if not text:
        return {"ok": False, "error": "必须提供整改措施 measures/action"}
    who = (owner or assignee or hazard.get("owner") or "待指派").strip()
    due = _TODAY + timedelta(days=int(due_days or 7))
    _ticket_seq += 1
    ticket = {
        "ticket_id": f"CA-{_ticket_seq}",
        "hazard_id": hazard_id,
        "hazard_title": hazard["title"],
        "measures": text,
        "action": text,  # alias for older clients/evals
        "owner": who,
        "assignee": who,
        "due_days": int(due_days or 7),
        "due_date": due.isoformat(),
        "status": "待执行",
        "evidence_note": "",
        "created_at": _TODAY.isoformat(),
    }
    _TICKETS.append(ticket)
    if hazard["status"] == "待整改":
        hazard["status"] = "整改中"
    return {"ok": True, "ticket": deepcopy(ticket), "hazard": _enrich(hazard)}


def list_corrective_tickets(
    hazard_id: str = "",
    status: str = "",
) -> dict[str, Any]:
    """List CAPA tickets, optional filter by hazard_id / status."""
    hid = (hazard_id or "").strip()
    st = (status or "").strip()
    items = []
    for t in _TICKETS:
        if hid and t["hazard_id"] != hid:
            continue
        if st and t["status"] != st:
            continue
        items.append(deepcopy(t))
    return {"count": len(items), "items": items}


def advance_corrective_ticket(
    ticket_id: str,
    action: str,
    evidence_note: str = "",
) -> dict[str, Any]:
    """Advance CAPA state machine: start | submit_verify | close | reject."""
    act = (action or "").strip().lower()
    if act not in _ADVANCE:
        return {
            "ok": False,
            "error": f"未知 action={action}，应为 start/submit_verify/close/reject",
        }
    ticket = next((t for t in _TICKETS if t["ticket_id"] == ticket_id), None)
    if not ticket:
        return {"ok": False, "error": f"未找到整改单 {ticket_id}"}
    expect_from, to_status = _ADVANCE[act]
    if ticket["status"] != expect_from:
        return {
            "ok": False,
            "error": f"{ticket_id} 当前状态为「{ticket['status']}」，{act} 仅允许从「{expect_from}」转入「{to_status}」",
        }
    if act == "submit_verify" and evidence_note:
        ticket["evidence_note"] = evidence_note.strip()
    if act == "close" and not (ticket.get("evidence_note") or evidence_note):
        return {"ok": False, "error": "关闭前须提供验收说明 evidence_note（或先在 submit_verify 写入）"}
    if act == "close" and evidence_note:
        ticket["evidence_note"] = (
            (ticket.get("evidence_note") or "") + " | 验收：" + evidence_note.strip()
        ).strip(" |")

    ticket["status"] = to_status
    hazard = _find_hazard(ticket["hazard_id"])
    if hazard:
        if act == "submit_verify":
            hazard["status"] = "待验收"
        elif act == "close":
            hazard["status"] = "已闭环"
            hazard["closed_at"] = _TODAY.isoformat()
        elif act == "reject":
            hazard["status"] = "整改中"
            ticket["evidence_note"] = (
                (ticket.get("evidence_note") or "") + " | 驳回：" + (evidence_note or "验收不通过")
            ).strip(" |")
        elif act == "start" and hazard["status"] == "待整改":
            hazard["status"] = "整改中"

    return {
        "ok": True,
        "ticket": deepcopy(ticket),
        "hazard": _enrich(hazard) if hazard else None,
        "transition": {"action": act, "from": expect_from, "to": to_status},
    }


def list_tickets() -> list[dict[str, Any]]:
    return deepcopy(_TICKETS)
