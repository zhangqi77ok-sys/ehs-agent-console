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
