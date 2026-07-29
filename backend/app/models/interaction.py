"""Histórico de interações/contatos de cobrança (tabulação).

Núcleo operacional da cobrança: registra cada tentativa de contato com o
titular, o canal, o resultado (tabulação) e eventuais promessas de pagamento.
"""
from __future__ import annotations

from datetime import date, datetime, timezone

from sqlalchemy import Date, DateTime, Float, ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


# Tabulações típicas de operação de cobrança.
#   cpc      = Contato com a Pessoa Certa
#   cpca     = Contato com a Pessoa Certa com Acordo
#   promessa = Promessa de Pagamento (PP)
#   recado   = Recado deixado com terceiro
#   sem_contato / numero_errado / nao_atende
RESULTS = {
    "cpc",
    "cpca",
    "promessa",
    "recado",
    "sem_contato",
    "numero_errado",
    "nao_atende",
    "acordo_fechado",
}
CHANNELS = {"telefone", "sms", "email", "whatsapp", "carta", "discador"}


class Interaction(Base):
    __tablename__ = "interactions"

    id: Mapped[int] = mapped_column(primary_key=True)
    debtor_id: Mapped[int] = mapped_column(
        ForeignKey("debtors.id", ondelete="CASCADE"), index=True, nullable=False
    )
    debt_id: Mapped[int | None] = mapped_column(
        ForeignKey("debts.id", ondelete="SET NULL"), index=True
    )

    channel: Mapped[str] = mapped_column(String(20), default="telefone")
    result: Mapped[str] = mapped_column(String(20), index=True, default="sem_contato")
    notes: Mapped[str | None] = mapped_column(String(1000))

    # Promessa de pagamento (quando result = promessa)
    promise_amount: Mapped[float | None] = mapped_column(Float)
    promise_date: Mapped[date | None] = mapped_column(Date)

    created_by: Mapped[int | None] = mapped_column(ForeignKey("users.id"))
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=_utcnow, index=True
    )

    debtor: Mapped["Debtor"] = relationship(back_populates="interactions")
