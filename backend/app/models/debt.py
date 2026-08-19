"""Dívida vinculada a um titular.

Tipos de carteira suportados:
    - ativa       : dívida ativa (crédito vencido geral)
    - consignado  : empréstimo consignado
    - concierge   : atendimento premium / carteira concierge
    - bancario    : cartões / financiamentos bancários
"""
from __future__ import annotations

from datetime import date, datetime, timezone

from sqlalchemy import Date, DateTime, Float, ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


class Debt(Base):
    __tablename__ = "debts"

    id: Mapped[int] = mapped_column(primary_key=True)
    debtor_id: Mapped[int] = mapped_column(
        ForeignKey("debtors.id", ondelete="CASCADE"), index=True, nullable=False
    )

    contract_ref: Mapped[str] = mapped_column(String(60), index=True, nullable=False)
    # ativa | consignado | concierge | bancario
    portfolio: Mapped[str] = mapped_column(String(20), index=True, nullable=False)
    creditor: Mapped[str] = mapped_column(String(160), nullable=False)

    original_amount: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    current_amount: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    due_date: Mapped[date | None] = mapped_column(Date)
    days_overdue: Mapped[int] = mapped_column(default=0)

    # pendente | negociacao | acordo | quitada | cancelada
    status: Mapped[str] = mapped_column(String(20), default="pendente", index=True)
    risk_score: Mapped[float] = mapped_column(Float, default=0.0)  # 0-100

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=_utcnow, onupdate=_utcnow
    )

    debtor: Mapped["Debtor"] = relationship(back_populates="debts")
    payments: Mapped[list["Payment"]] = relationship(
        back_populates="debt", cascade="all, delete-orphan"
    )
    agreements: Mapped[list["PaymentAgreement"]] = relationship(
        back_populates="debt", cascade="all, delete-orphan"
    )
