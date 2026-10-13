"""ind02_agent_spans

Revision ID: c4a22b8d9e01
Revises: b3e91f0a2c11
Create Date: 2026-10-13 15:20:00.000000
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "c4a22b8d9e01"
down_revision: Union[str, None] = "b3e91f0a2c11"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "agent_spans",
        sa.Column("span_id", sa.String(length=40), nullable=False),
        sa.Column("run_id", sa.String(length=40), nullable=False),
        sa.Column("parent_span_id", sa.String(length=40), nullable=True),
        sa.Column("kind", sa.String(length=16), nullable=False),
        sa.Column("name", sa.String(length=128), nullable=False),
        sa.Column("status", sa.String(length=16), nullable=False),
        sa.Column("step_index", sa.Integer(), nullable=False),
        sa.Column("duration_ms", sa.Integer(), nullable=False),
        sa.Column("attrs_json", sa.Text(), nullable=False),
        sa.Column("input_json", sa.Text(), nullable=False),
        sa.Column("output_json", sa.Text(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(["run_id"], ["agent_runs.run_id"]),
        sa.PrimaryKeyConstraint("span_id"),
    )
    op.create_index("ix_agent_spans_run_id", "agent_spans", ["run_id"])
    op.create_index("ix_agent_spans_kind", "agent_spans", ["kind"])


def downgrade() -> None:
    op.drop_index("ix_agent_spans_kind", table_name="agent_spans")
    op.drop_index("ix_agent_spans_run_id", table_name="agent_spans")
    op.drop_table("agent_spans")
