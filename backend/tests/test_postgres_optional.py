"""Optional Postgres connectivity check — skipped unless DATABASE_URL is postgres.

Default pytest (sqlite) never requires Docker. To exercise:

  DATABASE_URL=postgresql+psycopg://ehs:ehs_change_me@127.0.0.1:5432/ehs \\
    pytest -q tests/test_postgres_optional.py
"""

from __future__ import annotations

import os

import pytest

_URL = os.environ.get("DATABASE_URL", "")
_IS_PG = _URL.startswith("postgresql")


@pytest.mark.skipif(not _IS_PG, reason="DATABASE_URL is not postgresql*; default sqlite path")
def test_postgres_select_one() -> None:
    # Engine is created at import from settings.database_url — process must
    # already have DATABASE_URL=postgresql... when pytest starts.
    from sqlalchemy import text

    from app.db.session import engine

    assert "postgresql" in str(engine.url)
    with engine.connect() as conn:
        assert conn.execute(text("SELECT 1")).scalar() == 1
