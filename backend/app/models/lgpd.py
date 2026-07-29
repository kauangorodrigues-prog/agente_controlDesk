"""Modelos LGPD: registro de consentimento e requisições de titulares.

Base legal: Lei 13.709/2018 (LGPD).
 - ConsentRecord: art. 8º (consentimento) e art. 7º (bases legais).
 - DataSubjectRequest: art. 18 (direitos do titular).
"""
from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy import Boolean, DateTime, ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


class ConsentRecord(Base):
    """Registro de consentimento/base legal para tratamento de dados do titular."""

    __tablename__ = "consent_records"

    id: Mapped[int] = mapped_column(primary_key=True)
    debtor_id: Mapped[int] = mapped_column(
        ForeignKey("debtors.id", ondelete="CASCADE"), index=True, nullable=False
    )
    # Finalidade do tratamento (ex: "cobranca", "comunicacao", "score")
    purpose: Mapped[str] = mapped_column(String(80), nullable=False)
    # Base legal (art. 7º): consentimento | legitimo_interesse | obrigacao_legal |
    #                       execucao_contrato | protecao_credito
    legal_basis: Mapped[str] = mapped_column(String(40), default="legitimo_interesse")
    granted: Mapped[bool] = mapped_column(Boolean, default=True)
    channel: Mapped[str] = mapped_column(String(30), default="sistema")  # web | telefone | ...
    granted_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow)
    revoked_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class DataSubjectRequest(Base):
    """Requisição de exercício de direitos do titular (art. 18 da LGPD)."""

    __tablename__ = "data_subject_requests"

    id: Mapped[int] = mapped_column(primary_key=True)
    debtor_id: Mapped[int | None] = mapped_column(
        ForeignKey("debtors.id", ondelete="SET NULL"), index=True
    )
    requester_document: Mapped[str] = mapped_column(String(20), index=True)
    requester_email: Mapped[str | None] = mapped_column(String(180))
    # Verificação de identidade: e-mail informado confere com o cadastro do titular.
    identity_verified: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    # acesso | correcao | exclusao | portabilidade | anonimizacao | revogacao
    request_type: Mapped[str] = mapped_column(String(20), nullable=False)
    # recebida | em_analise | concluida | recusada
    status: Mapped[str] = mapped_column(String(15), default="recebida", index=True)
    notes: Mapped[str | None] = mapped_column(String(1000))
    handled_by: Mapped[int | None] = mapped_column(ForeignKey("users.id"))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow)
    resolved_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
