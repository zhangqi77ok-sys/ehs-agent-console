import os
import sys
from contextlib import asynccontextmanager
from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

os.environ.setdefault("DATABASE_URL", "sqlite:///./data/test_ehs.db")


@pytest.fixture()
def client(tmp_path, monkeypatch):
    db_file = tmp_path / "test.db"
    url = f"sqlite:///{db_file}"
    monkeypatch.setenv("DATABASE_URL", url)

    from app.config import Settings
    import app.config as config_mod
    import app.db.session as session_mod
    from app.db.base import Base
    from app.db import models  # noqa: F401
    from app.db.seed import seed_if_empty
    from app.db.session import get_db
    from app.main import create_app

    settings = Settings(database_url=url)
    config_mod.settings = settings

    engine = create_engine(
        url,
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    TestingSessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False)

    session_mod.engine = engine
    session_mod.SessionLocal = TestingSessionLocal

    db = TestingSessionLocal()
    try:
        seed_if_empty(db, tenant_id="demo-plant")
    finally:
        db.close()

    @asynccontextmanager
    async def _noop_lifespan(_app):
        yield

    app = create_app()
    app.router.lifespan_context = _noop_lifespan

    def _override_get_db():
        s = TestingSessionLocal()
        try:
            yield s
        finally:
            s.close()

    app.dependency_overrides[get_db] = _override_get_db

    with TestClient(app, raise_server_exceptions=True) as c:
        yield c

    app.dependency_overrides.clear()


@pytest.fixture()
def eng_headers():
    return {"X-Tenant-Id": "demo-plant", "X-Role": "ehs_engineer", "X-Actor": "eng-1"}


@pytest.fixture()
def viewer_headers():
    return {"X-Tenant-Id": "demo-plant", "X-Role": "viewer", "X-Actor": "view-1"}


@pytest.fixture()
def other_tenant_headers():
    return {"X-Tenant-Id": "other-plant", "X-Role": "ehs_engineer", "X-Actor": "other-eng"}
