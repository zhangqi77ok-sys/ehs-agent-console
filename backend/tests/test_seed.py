from sqlalchemy import create_engine, select, func
from sqlalchemy.orm import sessionmaker

from app.db.base import Base
from app.db.models import Hazard
from app.db.seed import seed_if_empty


def test_seed_inserts_at_least_four_demo_hazards(tmp_path):
    db_path = tmp_path / "seed.db"
    engine = create_engine(f"sqlite:///{db_path}", connect_args={"check_same_thread": False})
    Base.metadata.create_all(engine)
    Session = sessionmaker(bind=engine)
    session = Session()
    try:
        inserted = seed_if_empty(session, tenant_id="demo-plant")
        assert inserted >= 4
        demo_count = session.scalar(
            select(func.count()).select_from(Hazard).where(Hazard.tenant_id == "demo-plant")
        )
        assert demo_count >= 4
        # idempotent
        assert seed_if_empty(session, tenant_id="demo-plant") == 0
    finally:
        session.close()
