"""Trilha de auditoria — requisito de accountability da LGPD (art. 37).

Registra ações relevantes sobre dados pessoais e operações sensíveis.
"""
from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy import DateTime, Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


class AuditLog(Base):
    __tablename__ = "audit_logs"

    id: Mapped[int] = mapped_column(primary_key=True)
    actor_id: Mapped[int | None] = mapped_column(Integer, index=True)
    actor_email: Mapped[str | None] = mapped_column(String(180))
    action: Mapped[str] = mapped_column(String(60), index=True)  # ex: user.create
    entity: Mapped[str] = mapped_column(String(60), index=True)  # ex: debtor
    entity_id: Mapped[str | None] = mapped_column(String(60))
    detail: Mapped[str | None] = mapped_column(String(1000))
    ip_address: Mapped[str | None] = mapped_column(String(60))
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), index=True
    )
