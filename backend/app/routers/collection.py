"""Rotas de cobrança: devedores, dívidas, acordos e pagamentos."""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.deps import get_current_user
from app.models.debt import Debt
from app.models.debtor import Debtor
from app.models.payment import Payment, PaymentAgreement
from app.models.user import User
from app.schemas.collection import (
    AgreementCreate,
    AgreementOut,
    DebtCreate,
    DebtOut,
    DebtorCreate,
    DebtorOut,
    PaymentCreate,
    PaymentOut,
)
from app.services import audit
from app.services.scoring import recovery_score

router = APIRouter(prefix="/api/collection", tags=["Cobrança"])


# ── Devedores ────────────────────────────────────────────────────────────
@router.get("/debtors", response_model=list[DebtorOut])
def list_debtors(
    q: str | None = Query(default=None, description="Busca por nome ou documento"),
    limit: int = Query(default=50, le=200),
    db: Session = Depends(get_db),
    _: User = Depends(get_current_user),
):
    stmt = select(Debtor)
    if q:
        term = f"%{q.strip()}%"
        stmt = stmt.where((Debtor.full_name.ilike(term)) | (Debtor.document.ilike(term)))
    stmt = stmt.order_by(Debtor.full_name).limit(limit)
    return db.scalars(stmt).all()


@router.post("/debtors", response_model=DebtorOut, status_code=status.HTTP_201_CREATED)
def create_debtor(
    payload: DebtorCreate,
    request: Request,
    db: Session = Depends(get_db),
    actor: User = Depends(get_current_user),
):
    debtor = Debtor(**payload.model_dump())
    db.add(debtor)
    db.commit()
    db.refresh(debtor)
    audit.record(db, action="debtor.create", entity="debtor", entity_id=debtor.id,
                 actor=actor, request=request)
    return debtor


# ── Dívidas ──────────────────────────────────────────────────────────────
@router.get("/debts", response_model=list[DebtOut])
def list_debts(
    portfolio: str | None = None,
    status_filter: str | None = Query(default=None, alias="status"),
    debtor_id: int | None = None,
    db: Session = Depends(get_db),
    _: User = Depends(get_current_user),
):
    stmt = select(Debt)
    if portfolio:
        stmt = stmt.where(Debt.portfolio == portfolio)
    if status_filter:
        stmt = stmt.where(Debt.status == status_filter)
    if debtor_id:
        stmt = stmt.where(Debt.debtor_id == debtor_id)
    return db.scalars(stmt.order_by(Debt.created_at.desc()).limit(500)).all()


@router.post("/debts", response_model=DebtOut, status_code=status.HTTP_201_CREATED)
def create_debt(
    payload: DebtCreate,
    request: Request,
    db: Session = Depends(get_db),
    actor: User = Depends(get_current_user),
):
    if not db.get(Debtor, payload.debtor_id):
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Devedor não encontrado.")

    debt = Debt(**payload.model_dump())
    debt.risk_score = recovery_score(
        portfolio=debt.portfolio,
        days_overdue=debt.days_overdue,
        original_amount=debt.original_amount,
        current_amount=debt.current_amount,
    )
    db.add(debt)
    db.commit()
    db.refresh(debt)
    audit.record(db, action="debt.create", entity="debt", entity_id=debt.id,
                 actor=actor, request=request, detail=f"portfolio={debt.portfolio}")
    return debt


# ── Acordos ──────────────────────────────────────────────────────────────
@router.post("/agreements", response_model=AgreementOut, status_code=status.HTTP_201_CREATED)
def create_agreement(
    payload: AgreementCreate,
    request: Request,
    db: Session = Depends(get_db),
    actor: User = Depends(get_current_user),
):
    debt = db.get(Debt, payload.debt_id)
    if not debt:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Dívida não encontrada.")

    net = payload.total_amount * (1 - payload.discount_pct / 100)
    agreement = PaymentAgreement(
        debt_id=debt.id,
        total_amount=payload.total_amount,
        installments=payload.installments,
        installment_amount=round(net / payload.installments, 2),
        discount_pct=payload.discount_pct,
        created_by=actor.id,
    )
    debt.status = "acordo"
    db.add(agreement)
    db.commit()
    db.refresh(agreement)
    audit.record(db, action="agreement.create", entity="agreement", entity_id=agreement.id,
                 actor=actor, request=request)
    return agreement


# ── Pagamentos ───────────────────────────────────────────────────────────
@router.post("/payments", response_model=PaymentOut, status_code=status.HTTP_201_CREATED)
def register_payment(
    payload: PaymentCreate,
    request: Request,
    db: Session = Depends(get_db),
    actor: User = Depends(get_current_user),
):
    debt = db.get(Debt, payload.debt_id)
    if not debt:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Dívida não encontrada.")

    payment = Payment(debt_id=debt.id, amount=payload.amount, method=payload.method)
    debt.current_amount = max(0.0, debt.current_amount - payload.amount)
    if debt.current_amount == 0:
        debt.status = "quitada"
    db.add(payment)
    db.commit()
    db.refresh(payment)
    audit.record(db, action="payment.create", entity="payment", entity_id=payment.id,
                 actor=actor, request=request, detail=f"amount={payload.amount}")
    return payment
