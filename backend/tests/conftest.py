"""Eng-02: isolate SQLite before app modules bind the engine."""

from __future__ import annotations

import os
import tempfile
from pathlib import Path

# Must run before importing app.* (engine is created at import time).
_fd, _DB_PATH = tempfile.mkstemp(prefix="ehs_test_", suffix=".db")
os.close(_fd)
os.environ["DATABASE_URL"] = f"sqlite:///{_DB_PATH}"
os.environ["LLM_PROVIDER"] = "mock"  # never call real LLM in unit/API tests

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import delete

from app.db.base import Base
from app.db.models import ChatMessage, ChatSession, Hazard, Ticket
from app.db.seed import seed_if_empty
from app.db.session import SessionLocal, engine, init_db
from app.main import app


def _wipe_and_seed() -> None:
    db = SessionLocal()
    try:
        db.execute(delete(ChatMessage))
        db.execute(delete(ChatSession))
        db.execute(delete(Ticket))
        db.execute(delete(Hazard))
        db.commit()
    finally:
        db.close()
    seed_if_empty()


@pytest.fixture(scope="session", autouse=True)
def _prepare_db():
    Path(_DB_PATH).parent.mkdir(parents=True, exist_ok=True)
    Base.metadata.drop_all(bind=engine)
    init_db()
    seed_if_empty()
    yield
    try:
        os.unlink(_DB_PATH)
    except OSError:
        pass


@pytest.fixture
def client():
    """Fresh seed per test so CAPA mutations don't leak."""
    _wipe_and_seed()
    with TestClient(app) as c:
        yield c


@pytest.fixture
def repo_fresh():
    """Reset DB for direct repository / state-machine tests."""
    _wipe_and_seed()
    yield
