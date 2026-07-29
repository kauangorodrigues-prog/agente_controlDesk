"""Schemas de cobrança: devedores, dívidas, acordos e pagamentos."""
from __future__ import annotations

import re
from datetime import date, datetime

from pydantic import BaseModel, ConfigDict, Field, field_validator


# ── Devedor ──────────────────────────────────────────────────────────────
class DebtorBase(BaseModel):
    full_name: str = Field(min_length=2, max_length=200)
    document: str = Field(min_length=11, max_length=20)
    person_type: str = Field(default="PF", pattern="^(PF|PJ)$")
    email: str | None = None
    phone: str | None = None
    phone_alt: str | None = None
    birth_date: date | None = None
    zip_code: str | None = Field(default=None, max_length=9)
    address: str | None = None
    neighborhood: str | None = None
    city: str | None = None
    state: str | None = Field(default=None, max_length=2)

    @field_validator("document")
    @classmethod
    def only_digits(cls, v: str) -> str:
        digits = re.sub(r"\D", "", v)
        if len(digits) not in (11, 14):
            raise ValueError("Documento deve ter 11 (CPF) ou 14 (CNPJ) dígitos.")
        return digits


class DebtorCreate(DebtorBase):
    pass


class DebtorOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    full_name: str
    document_masked: str
    person_type: str
    email: str | None
    phone: str | None
    phone_alt: str | None
    birth_date: date | None
    zip_code: str | None
    address: str | None
    neighborhood: str | None
    city: str | None
    state: str | None
    contact_status: str
    is_anonymized: bool
    created_at: datetime


# ── Dívida ───────────────────────────────────────────────────────────────
PORTFOLIOS = {"ativa", "consignado", "concierge", "bancario"}


class DebtBase(BaseModel):
    contract_ref: str = Field(min_length=1, max_length=60)
    portfolio: str
    creditor: str = Field(min_length=1, max_length=160)
    original_amount: float = Field(ge=0)
    current_amount: float = Field(ge=0)
    due_date: date | None = None
    days_overdue: int = Field(default=0, ge=0)

    @field_validator("portfolio")
    @classmethod
    def valid_portfolio(cls, v: str) -> str:
        if v not in PORTFOLIOS:
            raise ValueError(f"portfolio deve ser um de: {sorted(PORTFOLIOS)}")
        return v


class DebtCreate(DebtBase):
    debtor_id: int


class DebtOut(DebtBase):
    model_config = ConfigDict(from_attributes=True)

    id: int
    debtor_id: int
    status: str
    risk_score: float
    created_at: datetime


# ── Acordo / Pagamento ───────────────────────────────────────────────────
class AgreementCreate(BaseModel):
    debt_id: int
    total_amount: float = Field(gt=0)
    installments: int = Field(default=1, ge=1, le=60)
    discount_pct: float = Field(default=0, ge=0, le=100)


class AgreementOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    debt_id: int
    total_amount: float
    installments: int
    installment_amount: float
    discount_pct: float
    status: str
    created_at: datetime


class PaymentCreate(BaseModel):
    debt_id: int
    amount: float = Field(gt=0)
    method: str = Field(default="pix", pattern="^(pix|boleto|cartao)$")


class PaymentOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    debt_id: int
    amount: float
    method: str
    paid_at: date


# ── Interação / Tabulação ────────────────────────────────────────────────
INTERACTION_RESULTS = {
    "cpc",
    "cpca",
    "promessa",
    "recado",
    "sem_contato",
    "numero_errado",
    "nao_atende",
    "acordo_fechado",
}
INTERACTION_CHANNELS = {"telefone", "sms", "email", "whatsapp", "carta", "discador"}


class InteractionCreate(BaseModel):
    debtor_id: int
    debt_id: int | None = None
    channel: str = Field(default="telefone")
    result: str = Field(default="sem_contato")
    notes: str | None = Field(default=None, max_length=1000)
    promise_amount: float | None = Field(default=None, ge=0)
    promise_date: date | None = None

    @field_validator("result")
    @classmethod
    def valid_result(cls, v: str) -> str:
        if v not in INTERACTION_RESULTS:
            raise ValueError(f"result deve ser um de: {sorted(INTERACTION_RESULTS)}")
        return v

    @field_validator("channel")
    @classmethod
    def valid_channel(cls, v: str) -> str:
        if v not in INTERACTION_CHANNELS:
            raise ValueError(f"channel deve ser um de: {sorted(INTERACTION_CHANNELS)}")
        return v


class InteractionOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    debtor_id: int
    debt_id: int | None
    channel: str
    result: str
    notes: str | None
    promise_amount: float | None
    promise_date: date | None
    created_at: datetime
