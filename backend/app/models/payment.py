"""Acordos e pagamentos vinculados a dívidas."""
from __future__ import annotations

from datetime import date, datetime, timezone

from sqlalchemy import Date, DateTime, Float, ForeignKey, Integer, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


class PaymentAgreement(Base):
    __tablename__ = "payment_agreements"

    id: Mapped[int] = mapped_column(primary_key=True)
    debt_id: Mapped[int] = mapped_column(
        ForeignKey("debts.id", ondelete="CASCADE"), index=True, nullable=False
    )
    total_amount: Mapped[float] = mapped_column(Float, nullable=False)
    installments: Mapped[int] = mapped_column(Integer, default=1)
    installment_amount: Mapped[float] = mapped_column(Float, default=0.0)
    discount_pct: Mapped[float] = mapped_column(Float, default=0.0)
    # vigente | quebrado | concluido
    status: Mapped[str] = mapped_column(String(20), default="vigente")
    created_by: Mapped[int | None] = mapped_column(ForeignKey("users.id"))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow)

    debt: Mapped["Debt"] = relationship(back_populates="agreements")


class Payment(Base):
    __tablename__ = "payments"

    id: Mapped[int] = mapped_column(primary_key=True)
    debt_id: Mapped[int] = mapped_column(
        ForeignKey("debts.id", ondelete="CASCADE"), index=True, nullable=False
    )
    amount: Mapped[float] = mapped_column(Float, nullable=False)
    paid_at: Mapped[date] = mapped_column(Date, default=lambda: _utcnow().date())
    method: Mapped[str] = mapped_column(String(20), default="pix")  # pix | boleto | cartao
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow)

    debt: Mapped["Debt"] = relationship(back_populates="payments")
