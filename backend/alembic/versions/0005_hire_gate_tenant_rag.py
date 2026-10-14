"""hire-gate: regulation_chunks.tenant_id for RAG tenant scoping

Revision ID: 0005_hire_gate
Revises: 0004_ch14_rag
Create Date: 2026-10-14
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "0005_hire_gate"
down_revision: Union[str, None] = "0004_ch14_rag"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "regulation_chunks",
        sa.Column("tenant_id", sa.String(64), nullable=False, server_default="demo-plant"),
    )
    op.create_index("ix_regulation_chunks_tenant_id", "regulation_chunks", ["tenant_id"])


def downgrade() -> None:
    op.drop_index("ix_regulation_chunks_tenant_id", table_name="regulation_chunks")
    op.drop_column("regulation_chunks", "tenant_id")
