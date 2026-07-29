"""Modelos do setor Planejamento: forecast e metas."""
from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy import DateTime, Float, Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


class Forecast(Base):
    __tablename__ = "forecasts"

    id: Mapped[int] = mapped_column(primary_key=True)
    reference_month: Mapped[str] = mapped_column(String(7), index=True)  # YYYY-MM
    portfolio: Mapped[str] = mapped_column(String(20), index=True)
    expected_recovery: Mapped[float] = mapped_column(Float, default=0.0)
    expected_volume: Mapped[int] = mapped_column(Integer, default=0)
    assumptions: Mapped[str | None] = mapped_column(String(500))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow)


class Goal(Base):
    __tablename__ = "goals"

    id: Mapped[int] = mapped_column(primary_key=True)
    reference_month: Mapped[str] = mapped_column(String(7), index=True)
    portfolio: Mapped[str] = mapped_column(String(20), index=True)
    target_amount: Mapped[float] = mapped_column(Float, default=0.0)
    achieved_amount: Mapped[float] = mapped_column(Float, default=0.0)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow)

    @property
    def attainment_pct(self) -> float:
        if not self.target_amount:
            return 0.0
        return round(self.achieved_amount / self.target_amount * 100, 2)
