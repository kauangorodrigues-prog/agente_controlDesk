"""Registro de notificações enviadas ao titular (régua de cobrança).

Guarda o histórico de comunicações para auditoria e prova de conformidade
(inclui bloqueios por ausência de base legal — LGPD).
"""
from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy import DateTime, ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


class Notification(Base):
    __tablename__ = "notifications"

    id: Mapped[int] = mapped_column(primary_key=True)
    debtor_id: Mapped[int] = mapped_column(
        ForeignKey("debtors.id", ondelete="CASCADE"), index=True, nullable=False
    )
    channel: Mapped[str] = mapped_column(String(20), default="email")
    template: Mapped[str] = mapped_column(String(40))
    subject: Mapped[str] = mapped_column(String(160))
    # enviado | simulado | sem_contato | bloqueado_lgpd | falha
    status: Mapped[str] = mapped_column(String(20), index=True, default="simulado")
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), index=True
    )
