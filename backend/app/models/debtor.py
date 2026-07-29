"""Titular/Devedor — pessoa física ou jurídica alvo da cobrança.

Contém dados pessoais sujeitos à LGPD. Campos sensíveis podem ser
anonimizados via solicitação do titular (ver módulo LGPD).
"""
from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy import Boolean, DateTime, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


class Debtor(Base):
    __tablename__ = "debtors"

    id: Mapped[int] = mapped_column(primary_key=True)
    # Documento (CPF/CNPJ) armazenado apenas com dígitos.
    document: Mapped[str] = mapped_column(String(20), index=True, nullable=False)
    person_type: Mapped[str] = mapped_column(String(2), default="PF")  # PF | PJ

    full_name: Mapped[str] = mapped_column(String(200), nullable=False)
    email: Mapped[str | None] = mapped_column(String(180))
    phone: Mapped[str | None] = mapped_column(String(30))
    city: Mapped[str | None] = mapped_column(String(120))
    state: Mapped[str | None] = mapped_column(String(2))

    # Flag LGPD: dados anonimizados após solicitação de exclusão do titular.
    is_anonymized: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    anonymized_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=_utcnow, onupdate=_utcnow
    )

    debts: Mapped[list["Debt"]] = relationship(
        back_populates="debtor", cascade="all, delete-orphan"
    )

    @property
    def document_masked(self) -> str:
        """Retorna o documento mascarado (data minimization em exibições)."""
        d = self.document or ""
        if len(d) <= 4:
            return "***"
        return f"{d[:3]}{'*' * (len(d) - 5)}{d[-2:]}"
