"""Ch21: optional live LLM eval — skipped unless LIVE_LLM_EVAL=1."""

from __future__ import annotations

import asyncio
import os

import pytest

pytestmark = pytest.mark.skipif(
    os.environ.get("LIVE_LLM_EVAL") != "1",
    reason="set LIVE_LLM_EVAL=1 (+ LLM_PROVIDER/openai credentials) for live eval",
)


def test_live_llm_one_case(monkeypatch):
    """Run a single chat turn against the configured real provider."""
    provider = os.environ.get("LLM_PROVIDER", "openai")
    if provider == "mock":
        pytest.skip("LIVE_LLM_EVAL=1 but LLM_PROVIDER=mock")

    from sqlalchemy import create_engine
    from sqlalchemy.orm import sessionmaker
    from sqlalchemy.pool import StaticPool

    from app.agent.loop import run_agent
    from app.config import Settings
    import app.config as config_mod
    from app.db.base import Base
    from app.db import models  # noqa: F401
    from app.db.seed import seed_if_empty

    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    Session = sessionmaker(bind=engine, autoflush=False, autocommit=False)
    config_mod.settings = Settings(
        database_url="sqlite://",
        llm_provider=provider,
        openai_api_key=os.environ.get("OPENAI_API_KEY", ""),
        openai_base_url=os.environ.get("OPENAI_BASE_URL", "https://api.openai.com/v1"),
        openai_model=os.environ.get("OPENAI_MODEL", "gpt-4o-mini"),
        hitl_enabled=False,
    )
    if not config_mod.settings.openai_api_key:
        pytest.skip("OPENAI_API_KEY missing")

    db = Session()
    try:
        seed_if_empty(db, tenant_id="demo-plant")
        result = asyncio.run(
            run_agent(
                "有哪些未闭环隐患？请简要列出。",
                db,
                tenant_id="demo-plant",
                role="ehs_engineer",
                actor="live-eval",
                hitl_enabled=False,
            )
        )
        assert result.get("status") in {"completed", "failed", "paused"}
        assert isinstance(result.get("reply"), str)
    finally:
        db.close()
