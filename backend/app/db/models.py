from __future__ import annotations

from datetime import date, datetime

from sqlalchemy import Boolean, Date, DateTime, ForeignKey, Integer, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .base import Base


class Hazard(Base):
    __tablename__ = "hazards"

    id: Mapped[str] = mapped_column(String(32), primary_key=True)
    title: Mapped[str] = mapped_column(String(256))
    description: Mapped[str] = mapped_column(Text, default="")
    plant: Mapped[str] = mapped_column(String(64), default="")
    area: Mapped[str] = mapped_column(String(128), default="")
    category: Mapped[str] = mapped_column(String(64), default="")
    level: Mapped[str] = mapped_column(String(16), default="一般")
    status: Mapped[str] = mapped_column(String(16), default="待整改", index=True)
    discoverer: Mapped[str] = mapped_column(String(64), default="")
    discovered_at: Mapped[str] = mapped_column(String(16), default="")
    deadline: Mapped[str] = mapped_column(String(16), default="", index=True)
    owner: Mapped[str] = mapped_column(String(64), default="")
    risk_note: Mapped[str] = mapped_column(Text, default="")
    closed_at: Mapped[str | None] = mapped_column(String(16), nullable=True)

    tickets: Mapped[list[Ticket]] = relationship(back_populates="hazard")


class Ticket(Base):
    __tablename__ = "tickets"

    ticket_id: Mapped[str] = mapped_column(String(32), primary_key=True)
    hazard_id: Mapped[str] = mapped_column(ForeignKey("hazards.id"), index=True)
    hazard_title: Mapped[str] = mapped_column(String(256), default="")
    measures: Mapped[str] = mapped_column(Text, default="")
    owner: Mapped[str] = mapped_column(String(64), default="")
    due_date: Mapped[str] = mapped_column(String(16), default="")
    status: Mapped[str] = mapped_column(String(16), default="待执行", index=True)
    evidence_note: Mapped[str] = mapped_column(Text, default="")
    created_at: Mapped[str] = mapped_column(String(16), default="")

    hazard: Mapped[Hazard] = relationship(back_populates="tickets")


class ChatSession(Base):
    __tablename__ = "chat_sessions"

    session_id: Mapped[str] = mapped_column(String(40), primary_key=True)
    tenant_id: Mapped[str] = mapped_column(String(64), default="default", index=True)
    role: Mapped[str] = mapped_column(String(64), default="ehs_engineer")
    turns: Mapped[int] = mapped_column(Integer, default=0)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    messages: Mapped[list[ChatMessage]] = relationship(
        back_populates="session", cascade="all, delete-orphan", order_by="ChatMessage.id"
    )


class ChatMessage(Base):
    __tablename__ = "chat_messages"
    __table_args__ = (UniqueConstraint("session_id", "seq", name="uq_session_seq"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    session_id: Mapped[str] = mapped_column(ForeignKey("chat_sessions.session_id"), index=True)
    seq: Mapped[int] = mapped_column(Integer)
    role: Mapped[str] = mapped_column(String(16))
    content: Mapped[str] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    session: Mapped[ChatSession] = relationship(back_populates="messages")


class AgentRun(Base):
    """Durable agent execution with checkpoint for crash/resume (Ind-01)."""

    __tablename__ = "agent_runs"

    run_id: Mapped[str] = mapped_column(String(40), primary_key=True)
    tenant_id: Mapped[str] = mapped_column(String(64), default="default", index=True)
    role: Mapped[str] = mapped_column(String(64), default="ehs_engineer")
    status: Mapped[str] = mapped_column(String(16), default="pending", index=True)
    # pending | running | paused | completed | failed
    message: Mapped[str] = mapped_column(Text, default="")
    reply: Mapped[str] = mapped_column(Text, default="")
    error: Mapped[str] = mapped_column(Text, default="")
    checkpoint_json: Mapped[str] = mapped_column(Text, default="{}")
    steps_json: Mapped[str] = mapped_column(Text, default="[]")
    budget_used: Mapped[int] = mapped_column(Integer, default=0)
    budget_max: Mapped[int] = mapped_column(Integer, default=8)
    session_id: Mapped[str | None] = mapped_column(String(40), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)


class AgentSpan(Base):
    """Span-level trace for one agent run (Ind-02)."""

    __tablename__ = "agent_spans"

    span_id: Mapped[str] = mapped_column(String(40), primary_key=True)
    run_id: Mapped[str] = mapped_column(String(40), ForeignKey("agent_runs.run_id"), index=True)
    parent_span_id: Mapped[str | None] = mapped_column(String(40), nullable=True)
    kind: Mapped[str] = mapped_column(String(16), default="tool", index=True)  # llm | tool | note | run
    name: Mapped[str] = mapped_column(String(128), default="")
    status: Mapped[str] = mapped_column(String(16), default="ok")  # ok | error | denied | timeout
    step_index: Mapped[int] = mapped_column(Integer, default=0)
    duration_ms: Mapped[int] = mapped_column(Integer, default=0)
    attrs_json: Mapped[str] = mapped_column(Text, default="{}")
    input_json: Mapped[str] = mapped_column(Text, default="{}")
    output_json: Mapped[str] = mapped_column(Text, default="{}")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)


class AgentApproval(Base):
    """HITL gate for write tools (Ind-03)."""

    __tablename__ = "agent_approvals"

    approval_id: Mapped[str] = mapped_column(String(40), primary_key=True)
    run_id: Mapped[str] = mapped_column(String(40), ForeignKey("agent_runs.run_id"), index=True)
    tool_name: Mapped[str] = mapped_column(String(128), default="")
    arguments_json: Mapped[str] = mapped_column(Text, default="{}")
    call_id: Mapped[str] = mapped_column(String(40), default="")
    status: Mapped[str] = mapped_column(String(16), default="pending", index=True)
    # pending | approved | rejected
    decided_by: Mapped[str] = mapped_column(String(64), default="")
    note: Mapped[str] = mapped_column(Text, default="")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    decided_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
