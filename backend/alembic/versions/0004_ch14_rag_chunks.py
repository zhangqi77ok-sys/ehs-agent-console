"""ch14 regulation chunks for postgres/sqlite RAG path

Revision ID: 0004_ch14_rag
Revises: 0003_ch10_sessions
Create Date: 2026-10-13

Stores embeddings as JSON text (portable). On Postgres with pgvector image,
docs explain optional ALTER to vector(256). Extension create is best-effort.
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "0004_ch14_rag"
down_revision: Union[str, None] = "0003_ch10_sessions"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    bind = op.get_bind()
    if bind.dialect.name == "postgresql":
        op.execute("CREATE EXTENSION IF NOT EXISTS vector")
    op.create_table(
        "regulation_chunks",
        sa.Column("id", sa.String(128), primary_key=True),
        sa.Column("source", sa.String(256), nullable=False, server_default=""),
        sa.Column("text", sa.Text(), nullable=False, server_default=""),
        sa.Column("embedding_json", sa.Text(), nullable=False, server_default="[]"),
        sa.Column("dim", sa.Integer(), nullable=False, server_default="256"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_index("ix_regulation_chunks_source", "regulation_chunks", ["source"])
    # Optional pgvector column — only on postgres; keep JSON as source of truth for sqlite/tests
    if bind.dialect.name == "postgresql":
        try:
            op.execute("ALTER TABLE regulation_chunks ADD COLUMN IF NOT EXISTS embedding vector(256)")
        except Exception:
            # extension missing in some CI images — JSON path still works
            pass


def downgrade() -> None:
    op.drop_index("ix_regulation_chunks_source", table_name="regulation_chunks")
    op.drop_table("regulation_chunks")
