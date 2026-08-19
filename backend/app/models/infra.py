"""Modelos do setor Infraestrutura: incidentes e health checks."""
from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy import DateTime, Float, String
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


class Incident(Base):
    __tablename__ = "incidents"

    id: Mapped[int] = mapped_column(primary_key=True)
    title: Mapped[str] = mapped_column(String(160), nullable=False)
    description: Mapped[str | None] = mapped_column(String(1000))
    # baixa | media | alta | critica
    severity: Mapped[str] = mapped_column(String(10), default="media", index=True)
    # aberto | investigando | mitigado | resolvido
    status: Mapped[str] = mapped_column(String(15), default="aberto", index=True)
    service: Mapped[str] = mapped_column(String(80), default="core")
    opened_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow)
    resolved_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class SystemHealthCheck(Base):
    __tablename__ = "system_health_checks"

    id: Mapped[int] = mapped_column(primary_key=True)
    service: Mapped[str] = mapped_column(String(80), index=True)
    status: Mapped[str] = mapped_column(String(15), default="up")  # up | degraded | down
    latency_ms: Mapped[float] = mapped_column(Float, default=0.0)
    cpu_pct: Mapped[float] = mapped_column(Float, default=0.0)
    mem_pct: Mapped[float] = mapped_column(Float, default=0.0)
    checked_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow)
