"""Ch14 postgres RAG path — skip live sync without postgres."""

from __future__ import annotations

import os

import pytest

from app.rag.pg_store import is_postgres_url, get_active_regulations_store, sync_chunks_to_db
from app.rag.store import RegulationsStore


def test_is_postgres_url_detect():
    assert is_postgres_url("postgresql+psycopg://u:p@localhost/db")
    assert is_postgres_url("postgres://u:p@localhost/db")
    assert not is_postgres_url("sqlite:///./data/ehs.db")


def test_active_store_sqlite_is_memory(monkeypatch):
    from app.config import Settings
    import app.config as config_mod

    config_mod.settings = Settings(database_url="sqlite:///./data/x.db")
    store = get_active_regulations_store()
    assert isinstance(store, RegulationsStore)


@pytest.mark.skipif(
    not os.getenv("EHS_PG_TEST_URL"),
    reason="Set EHS_PG_TEST_URL to run live postgres RAG sync",
)
def test_sync_chunks_live_postgres(monkeypatch):
    url = os.environ["EHS_PG_TEST_URL"]
    from app.config import Settings
    import app.config as config_mod
    import app.db.session as session_mod
    from sqlalchemy import create_engine
    from sqlalchemy.orm import sessionmaker
    from app.db.base import Base
    from app.db import models  # noqa: F401

    config_mod.settings = Settings(database_url=url)
    engine = create_engine(url)
    Base.metadata.create_all(engine)
    Session = sessionmaker(bind=engine, autoflush=False, autocommit=False)
    session_mod.engine = engine
    session_mod.SessionLocal = Session
    n = sync_chunks_to_db()
    assert n > 0
    store = get_active_regulations_store()
    hits = store.search("灭火器", top_k=2)
    assert hits
    assert hits[0].get("backend") == "postgres"
