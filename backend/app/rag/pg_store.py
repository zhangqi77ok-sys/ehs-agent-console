"""Postgres-backed RAG chunk store (Ch14). Falls back to in-memory if not postgres."""

from __future__ import annotations

import json
from typing import Any

from sqlalchemy import delete, select, text

from app.config import settings
from app.db.models import RegulationChunk
from app.db import session as db_session
from app.rag.chunk import load_markdown_dir
from app.rag.embed import cosine, embed_text
from app.rag.store import _DEFAULT_DIR, get_regulations_store


def is_postgres_url(url: str | None = None) -> bool:
    u = (url or settings.database_url or "").lower()
    return u.startswith("postgresql") or u.startswith("postgres")


def sync_chunks_to_db(root=None, *, dim: int = 256) -> int:
    """Load markdown regulations into regulation_chunks (idempotent replace)."""
    if not is_postgres_url():
        return 0
    chunks = load_markdown_dir(root or _DEFAULT_DIR)
    db = db_session.SessionLocal()
    try:
        db.execute(delete(RegulationChunk))
        for c in chunks:
            vec = embed_text(c["text"], dim=dim)
            row = RegulationChunk(
                id=c["id"],
                source=c.get("source") or "",
                text=c["text"],
                embedding_json=json.dumps(vec),
                dim=dim,
            )
            db.add(row)
        db.commit()
        # best-effort fill vector column if present
        try:
            db.execute(text(
                "UPDATE regulation_chunks SET embedding = embedding_json::vector "
                "WHERE embedding IS NULL"
            ))
            db.commit()
        except Exception:
            db.rollback()
        return len(chunks)
    finally:
        db.close()


class PostgresRegulationsStore:
    """Search using DB-stored embedding_json (cosine in Python — portable)."""

    def __init__(self, dim: int = 256):
        self.dim = dim

    def search(self, query: str, *, top_k: int = 3) -> list[dict[str, Any]]:
        db = db_session.SessionLocal()
        try:
            rows = list(db.scalars(select(RegulationChunk)).all())
            if not rows:
                # auto-seed once
                db.close()
                sync_chunks_to_db(dim=self.dim)
                db = db_session.SessionLocal()
                rows = list(db.scalars(select(RegulationChunk)).all())
            q = embed_text(query, dim=self.dim)
            scored = []
            for row in rows:
                try:
                    vec = json.loads(row.embedding_json or "[]")
                except json.JSONDecodeError:
                    vec = embed_text(row.text, dim=self.dim)
                score = cosine(q, vec) if vec else 0.0
                scored.append((score, row))
            scored.sort(key=lambda x: x[0], reverse=True)
            out = []
            for score, row in scored[: max(1, top_k)]:
                out.append(
                    {
                        "id": row.id,
                        "source": row.source,
                        "text": row.text,
                        "score": round(float(score), 4),
                        "backend": "postgres",
                    }
                )
            return out
        finally:
            db.close()


def get_active_regulations_store():
    """Prefer postgres DB store when DATABASE_URL is postgres; else in-memory."""
    if is_postgres_url():
        return PostgresRegulationsStore()
    return get_regulations_store()
