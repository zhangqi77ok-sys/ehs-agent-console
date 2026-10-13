"""Ch6: optional Postgres URL parsing (no live server required)."""

from app.db.session import _connect_args


def test_sqlite_connect_args():
    assert _connect_args("sqlite:///./data/ehs.db") == {"check_same_thread": False}


def test_postgres_connect_args_empty():
    assert _connect_args("postgresql+psycopg://ehs:ehs@localhost:5432/ehs") == {}
