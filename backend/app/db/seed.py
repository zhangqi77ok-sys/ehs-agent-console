"""Seed demo hazards/tickets if DB empty."""

from __future__ import annotations

from sqlalchemy import func, select

from .models import Hazard, Ticket
from .session import SessionLocal

_SEED_HAZARDS = [
    dict(id="HZ-2026-001", title="车间西侧灭火器压力不足/过期", description="一号车间西侧通道挂墙灭火器指针进入红区，标签显示点检过期。", plant="一号车间", area="西侧疏散通道", category="消防", level="一般", status="待整改", discoverer="巡检员-赵六", discovered_at="2026-10-01", deadline="2026-10-15", owner="张三", risk_note="初期火灾扑救能力下降，影响疏散通道合规。"),
    dict(id="HZ-2026-002", title="配电柜柜门未上锁、无警示标识", description="配电房 A 低压柜门可随意开启，缺少「有电危险」标识与上锁挂牌。", plant="动力车间", area="配电房 A", category="电气", level="重大", status="整改中", discoverer="EHS-李四", discovered_at="2026-10-05", deadline="2026-10-08", owner="李四", risk_note="可能发生触电或误操作停电，须立即管控。"),
    dict(id="HZ-2026-003", title="安全通道堆放纸箱堵塞", description="二号仓库北门疏散通道堆放成品纸箱，净宽不足。", plant="二号仓库", area="北门疏散通道", category="消防", level="一般", status="已闭环", discoverer="仓管-王五", discovered_at="2026-09-20", deadline="2026-09-27", owner="王五", risk_note="火灾时影响疏散；已清运并复核拍照。", closed_at="2026-09-26"),
    dict(id="HZ-2026-004", title="冲压工位防护罩缺失", description="三号车间 3# 冲床安全防护罩拆卸后未复位，点动试机无连锁。", plant="三号车间", area="冲压线 3#", category="机械", level="重大", status="待整改", discoverer="班长-周七", discovered_at="2026-10-10", deadline="2026-10-12", owner="周七", risk_note="机械伤害高风险，建议停机挂牌。"),
    dict(id="HZ-2026-005", title="危化品暂存间台账与实物不符", description="危化品库丙酮账面 4 桶、实物 3 桶，领用单缺签字。", plant="危化品库", area="暂存间 B", category="危化", level="重大", status="待验收", discoverer="EHS-钱八", discovered_at="2026-10-03", deadline="2026-10-10", owner="钱八", risk_note="账实不符可能掩盖泄漏或私自领用。"),
    dict(id="HZ-2026-006", title="叉车日检表连续三天空白", description="物流区 2 号电动叉车班前检查表 10/10–10/12 无记录。", plant="物流区", area="叉车停放区", category="机械", level="一般", status="整改中", discoverer="物流主管-孙九", discovered_at="2026-10-12", deadline="2026-10-20", owner="孙九", risk_note="未落实班前检查，碰撞/倾覆风险上升。"),
    dict(id="HZ-2026-007", title="有限空间作业未办票", description="污水池清淤当日无有限空间作业票，现场无气体检测记录。", plant="公用工程", area="污水池", category="有限空间", level="重大", status="待整改", discoverer="安全员-吴十", discovered_at="2026-10-11", deadline="2026-10-11", owner="吴十", risk_note="中毒窒息风险极高，须立即停工补票。"),
    dict(id="HZ-2026-008", title="应急照明抽检不亮", description="办公楼二层疏散指示灯抽检 2/6 不亮。", plant="办公楼", area="二层走廊", category="消防", level="一般", status="已闭环", discoverer="物业-郑一", discovered_at="2026-09-15", deadline="2026-09-22", owner="郑一", risk_note="已更换灯具并复测。", closed_at="2026-09-21"),
    dict(id="HZ-2026-009", title="气瓶未固定、无防倾倒链", description="焊接区氧气/乙炔瓶直立但无防倾倒链条，间距不足。", plant="一号车间", area="焊接区", category="危化", level="一般", status="待整改", discoverer="巡检员-赵六", discovered_at="2026-10-09", deadline="2026-10-18", owner="张三", risk_note="倾倒可能导致阀门损坏与泄漏。"),
    dict(id="HZ-2026-010", title="动火作业监护人离岗", description="机修动火点监护人离开超过 15 分钟，灭火器未放置到位。", plant="机修车间", area="管道改造点", category="动火", level="重大", status="整改中", discoverer="EHS-李四", discovered_at="2026-10-08", deadline="2026-10-09", owner="李四", risk_note="动火失控风险；已暂停作业待重新交底。"),
    dict(id="HZ-2026-011", title="劳保用品发放台账缺项", description="打磨岗位近两月防护眼镜领用记录缺失。", plant="三号车间", area="打磨工位", category="职业健康", level="一般", status="待验收", discoverer="HR-陈二", discovered_at="2026-10-06", deadline="2026-10-16", owner="陈二", risk_note="职业伤害防护不足，验收看补发与培训记录。"),
    dict(id="HZ-2026-012", title="雨污水混排迹象", description="厂界雨水井目视有乳化液泡沫，疑似工艺废水混入。", plant="厂界", area="东侧雨水井", category="环保", level="重大", status="待整改", discoverer="环保专员-冯三", discovered_at="2026-10-12", deadline="2026-10-14", owner="冯三", risk_note="环境违法风险，须溯源封堵并监测。"),
]

_SEED_TICKETS = [
    dict(ticket_id="CA-101", hazard_id="HZ-2026-002", hazard_title="配电柜柜门未上锁、无警示标识", measures="加装挂锁与警示标识，完成上锁挂牌培训", owner="李四", due_date="2026-10-08", status="执行中", evidence_note="", created_at="2026-10-05"),
    dict(ticket_id="CA-102", hazard_id="HZ-2026-005", hazard_title="危化品暂存间台账与实物不符", measures="盘点补录、追查领用单、修订双人双锁制度", owner="钱八", due_date="2026-10-10", status="待验收", evidence_note="已盘点并补签字，待 EHS 复核", created_at="2026-10-04"),
]


def seed_if_empty() -> dict[str, int]:
    db = SessionLocal()
    try:
        n = db.scalar(select(func.count()).select_from(Hazard)) or 0
        if n > 0:
            return {"hazards": n, "tickets": db.scalar(select(func.count()).select_from(Ticket)) or 0, "seeded": 0}
        for row in _SEED_HAZARDS:
            db.add(Hazard(**row))
        for row in _SEED_TICKETS:
            db.add(Ticket(**row))
        db.commit()
        return {"hazards": len(_SEED_HAZARDS), "tickets": len(_SEED_TICKETS), "seeded": 1}
    finally:
        db.close()
