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
    city: str | None
    state: str | None
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
