from datetime import date, datetime, timezone

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.db.models import Hazard

DEFAULT_TENANT = "demo-plant"


def seed_if_empty(session: Session, tenant_id: str = DEFAULT_TENANT) -> int:
    """Insert demo hazards when the tenant has none. Returns inserted count."""
    count = session.scalar(
        select(func.count()).select_from(Hazard).where(Hazard.tenant_id == tenant_id)
    )
    if count and count > 0:
        return 0

    now = datetime.now(timezone.utc)
    hazards = [
        Hazard(
            id="HZ-2026-001",
            tenant_id=tenant_id,
            title="灭火器过期未更换",
            description="A区消防通道旁灭火器压力表已入红区，且铭牌有效期已过。",
            plant="一厂",
            area="A区消防通道",
            category="消防",
            level="重大",
            status="待整改",
            owner="张工",
            deadline=date(2026, 10, 20),
            discoverer="巡检员李某",
            discovered_at=now,
            risk_note="一旦起火初期扑救能力不足",
        ),
        Hazard(
            id="HZ-2026-002",
            tenant_id=tenant_id,
            title="配电箱接地线松动",
            description="B车间配电箱PE线端子松动，存在触电风险。",
            plant="一厂",
            area="B车间配电间",
            category="电气",
            level="重大",
            status="待整改",
            owner="王电工",
            deadline=date(2026, 10, 18),
            discoverer="安全员赵某",
            discovered_at=now,
            risk_note="漏电保护可能失效",
        ),
        Hazard(
            id="HZ-2026-003",
            tenant_id=tenant_id,
            title="叉车通道反光镜缺失",
            description="C仓库转弯处反光镜脱落，盲区增大。",
            plant="二厂",
            area="C仓库",
            category="车辆/物流",
            level="一般",
            status="待整改",
            owner="刘班长",
            deadline=date(2026, 10, 25),
            discoverer="仓库主管",
            discovered_at=now,
        ),
        Hazard(
            id="HZ-2026-004",
            tenant_id=tenant_id,
            title="危化品暂存区标识模糊",
            description="危化品暂存区分类标签褪色，易混放。",
            plant="二厂",
            area="危化品暂存区",
            category="危化品",
            level="一般",
            status="待整改",
            owner="陈仓管",
            deadline=date(2026, 10, 30),
            discoverer="EHS督察",
            discovered_at=now,
        ),
        Hazard(
            id="HZ-2026-005",
            tenant_id="other-plant",
            title="他厂隐患（跨租户演示）",
            description="仅用于验证跨租户隔离，不应出现在 demo-plant 列表。",
            plant="他厂",
            area="X区",
            category="其他",
            level="一般",
            status="待整改",
            owner="外厂",
            deadline=date(2026, 11, 1),
            discoverer="system",
            discovered_at=now,
        ),
    ]
    session.add_all(hazards)
    session.commit()
    return len(hazards)
