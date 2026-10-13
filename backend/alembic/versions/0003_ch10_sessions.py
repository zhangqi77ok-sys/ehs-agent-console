"""ch10 agent sessions

Revision ID: 0003_ch10_sessions
Revises: 0002_ch4_runs
Create Date: 2026-10-13
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "0003_ch10_sessions"
down_revision: Union[str, None] = "0002_ch4_runs"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "agent_sessions",
        sa.Column("session_id", sa.String(64), primary_key=True),
        sa.Column("tenant_id", sa.String(64), nullable=False),
        sa.Column("actor", sa.String(64), nullable=False, server_default=""),
        sa.Column("messages_json", sa.Text(), nullable=False, server_default="[]"),
        sa.Column("summary", sa.Text(), nullable=False, server_default=""),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_index("ix_agent_sessions_tenant_id", "agent_sessions", ["tenant_id"])


def downgrade() -> None:
    op.drop_index("ix_agent_sessions_tenant_id", table_name="agent_sessions")
    op.drop_table("agent_sessions")
