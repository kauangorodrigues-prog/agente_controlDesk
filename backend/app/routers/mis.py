"""Setor MIS: indicadores consolidados e business intelligence.

Todos os números são agregados — não expõem dados pessoais (data minimization).
"""
from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.deps import require_sector
from app.core.rbac import Sector
from app.models.debt import Debt
from app.models.payment import Payment
from app.models.user import User

router = APIRouter(prefix="/api/mis", tags=["Setor · MIS"])
_guard = require_sector(Sector.MIS)


@router.get("/overview")
def overview(db: Session = Depends(get_db), _: User = Depends(_guard)):
    total_debts = db.scalar(select(func.count(Debt.id))) or 0
    total_outstanding = db.scalar(select(func.coalesce(func.sum(Debt.current_amount), 0.0)))
    total_recovered = db.scalar(select(func.coalesce(func.sum(Payment.amount), 0.0)))
    quitadas = db.scalar(select(func.count(Debt.id)).where(Debt.status == "quitada")) or 0

    recovery_rate = round((quitadas / total_debts * 100), 1) if total_debts else 0.0
    return {
        "total_debts": total_debts,
        "total_outstanding": round(float(total_outstanding), 2),
        "total_recovered": round(float(total_recovered), 2),
        "debts_settled": quitadas,
        "settlement_rate_pct": recovery_rate,
    }


@router.get("/by-portfolio")
def by_portfolio(db: Session = Depends(get_db), _: User = Depends(_guard)):
    rows = db.execute(
        select(
            Debt.portfolio,
            func.count(Debt.id),
            func.coalesce(func.sum(Debt.current_amount), 0.0),
            func.coalesce(func.avg(Debt.risk_score), 0.0),
        ).group_by(Debt.portfolio)
    ).all()
    return [
        {
            "portfolio": r[0],
            "count": r[1],
            "outstanding": round(float(r[2]), 2),
            "avg_risk_score": round(float(r[3]), 1),
        }
        for r in rows
    ]


@router.get("/by-status")
def by_status(db: Session = Depends(get_db), _: User = Depends(_guard)):
    rows = db.execute(
        select(Debt.status, func.count(Debt.id)).group_by(Debt.status)
    ).all()
    return [{"status": r[0], "count": r[1]} for r in rows]
