"""
SQLAlchemy ORM tables + async session factory.
Using SQLite + aiosqlite for zero-infra demo.
"""
from __future__ import annotations
from datetime import datetime
from typing import AsyncGenerator
from sqlalchemy import String, Text, Float, Integer, DateTime, JSON, create_engine
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column

from app.core.config import settings


# ---------------------------------------------------------------------------
# Engine + session
# ---------------------------------------------------------------------------

async_engine = create_async_engine(settings.database_url, echo=False)
AsyncSessionLocal = async_sessionmaker(async_engine, expire_on_commit=False)


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    async with AsyncSessionLocal() as session:
        yield session


# ---------------------------------------------------------------------------
# ORM Base + Tables
# ---------------------------------------------------------------------------

class Base(DeclarativeBase):
    pass


class TicketORM(Base):
    __tablename__ = "tickets"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    customer_id: Mapped[str] = mapped_column(String(50), index=True)
    status: Mapped[str] = mapped_column(String(20), default="open")
    intent: Mapped[str | None] = mapped_column(String(20), nullable=True)
    urgency: Mapped[str | None] = mapped_column(String(20), nullable=True)
    sentiment: Mapped[str | None] = mapped_column(String(20), nullable=True)
    messages_json: Mapped[str] = mapped_column(Text, default="[]")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    resolved_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    resolution_time_seconds: Mapped[float | None] = mapped_column(Float, nullable=True)


class AgentFindingORM(Base):
    __tablename__ = "agent_findings"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    ticket_id: Mapped[str] = mapped_column(String(36), index=True)
    agent_name: Mapped[str] = mapped_column(String(50))
    summary: Mapped[str] = mapped_column(Text)
    evidence_json: Mapped[str] = mapped_column(Text, default="[]")
    confidence: Mapped[float] = mapped_column(Float)
    actions_available_json: Mapped[str] = mapped_column(Text, default="[]")
    root_cause: Mapped[str | None] = mapped_column(Text, nullable=True)
    raw_data_json: Mapped[str] = mapped_column(Text, default="{}")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)


class TraceEventORM(Base):
    __tablename__ = "trace_events"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    ticket_id: Mapped[str] = mapped_column(String(36), index=True)
    event_type: Mapped[str] = mapped_column(String(50))
    agent_name: Mapped[str | None] = mapped_column(String(50), nullable=True)
    payload_json: Mapped[str] = mapped_column(Text, default="{}")
    message: Mapped[str] = mapped_column(Text)
    timestamp: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)


class EscalationPacketORM(Base):
    __tablename__ = "escalation_packets"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    ticket_id: Mapped[str] = mapped_column(String(36), index=True)
    customer_id: Mapped[str] = mapped_column(String(50))
    justification: Mapped[str] = mapped_column(Text)
    issue_summary: Mapped[str] = mapped_column(Text)
    systems_checked_json: Mapped[str] = mapped_column(Text, default="[]")
    findings_summary_json: Mapped[str] = mapped_column(Text, default="[]")
    actions_attempted_json: Mapped[str] = mapped_column(Text, default="[]")
    sentiment_trend_json: Mapped[str] = mapped_column(Text, default="[]")
    recommended_next_step: Mapped[str] = mapped_column(Text)
    priority: Mapped[str] = mapped_column(String(20))
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)


async def create_tables() -> None:
    async with async_engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
