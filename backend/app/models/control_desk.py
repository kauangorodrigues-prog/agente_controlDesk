"""Modelos do setor Control Desk: campanhas de discagem e snapshots de pacing."""
from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy import Boolean, DateTime, Float, Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


class Campaign(Base):
    __tablename__ = "campaigns"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(120), nullable=False)
    portfolio: Mapped[str] = mapped_column(String(20), index=True)  # tipo de carteira
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)

    pacing: Mapped[float] = mapped_column(Float, default=2.0)  # chamadas/agente
    agents_online: Mapped[int] = mapped_column(Integer, default=0)
    mailing_total: Mapped[int] = mapped_column(Integer, default=0)
    mailing_worked: Mapped[int] = mapped_column(Integer, default=0)

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=_utcnow, onupdate=_utcnow
    )


class PacingSnapshot(Base):
    __tablename__ = "pacing_snapshots"

    id: Mapped[int] = mapped_column(primary_key=True)
    campaign_id: Mapped[int] = mapped_column(Integer, index=True)
    idle_pct: Mapped[float] = mapped_column(Float, default=0.0)
    abandon_pct: Mapped[float] = mapped_column(Float, default=0.0)
    calls_made: Mapped[int] = mapped_column(Integer, default=0)
    contacts: Mapped[int] = mapped_column(Integer, default=0)
    promises: Mapped[int] = mapped_column(Integer, default=0)
    captured_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow)
