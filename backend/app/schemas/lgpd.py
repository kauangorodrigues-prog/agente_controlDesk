"""Schemas do módulo LGPD."""
from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field

CONSENT_BASES = {
    "consentimento",
    "legitimo_interesse",
    "obrigacao_legal",
    "execucao_contrato",
    "protecao_credito",
}
REQUEST_TYPES = {
    "acesso",
    "correcao",
    "exclusao",
    "portabilidade",
    "anonimizacao",
    "revogacao",
}


class ConsentCreate(BaseModel):
    debtor_id: int
    purpose: str = Field(min_length=1, max_length=80)
    legal_basis: str = Field(default="legitimo_interesse")
    granted: bool = True
    channel: str = Field(default="sistema", max_length=30)


class ConsentOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    debtor_id: int
    purpose: str
    legal_basis: str
    granted: bool
    channel: str
    granted_at: datetime
    revoked_at: datetime | None


class DSRCreate(BaseModel):
    """Data Subject Request — pode ser aberta pelo próprio titular."""

    requester_document: str = Field(min_length=11, max_length=20)
    requester_email: str | None = None
    request_type: str
    notes: str | None = None


class DSRUpdate(BaseModel):
    status: str = Field(pattern="^(recebida|em_analise|concluida|recusada)$")
    notes: str | None = None


class DSROut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    debtor_id: int | None
    requester_document: str
    requester_email: str | None
    identity_verified: bool
    request_type: str
    status: str
    notes: str | None
    created_at: datetime
    resolved_at: datetime | None
