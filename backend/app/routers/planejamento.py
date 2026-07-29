"""Setor Planejamento: forecast e metas por carteira."""
from __future__ import annotations

from fastapi import APIRouter, Depends, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.deps import require_sector
from app.core.rbac import Sector
from app.models.planning import Forecast, Goal
from app.models.user import User
from app.schemas.sectors import ForecastCreate, ForecastOut, GoalCreate, GoalOut

router = APIRouter(prefix="/api/planejamento", tags=["Setor · Planejamento"])
_guard = require_sector(Sector.PLANEJAMENTO)


@router.get("/forecasts", response_model=list[ForecastOut])
def list_forecasts(db: Session = Depends(get_db), _: User = Depends(_guard)):
    return db.scalars(select(Forecast).order_by(Forecast.reference_month.desc())).all()


@router.post("/forecasts", response_model=ForecastOut, status_code=status.HTTP_201_CREATED)
def create_forecast(
    payload: ForecastCreate, db: Session = Depends(get_db), _: User = Depends(_guard)
):
    forecast = Forecast(**payload.model_dump())
    db.add(forecast)
    db.commit()
    db.refresh(forecast)
    return forecast


@router.get("/goals", response_model=list[GoalOut])
def list_goals(db: Session = Depends(get_db), _: User = Depends(_guard)):
    return db.scalars(select(Goal).order_by(Goal.reference_month.desc())).all()


@router.post("/goals", response_model=GoalOut, status_code=status.HTTP_201_CREATED)
def create_goal(
    payload: GoalCreate, db: Session = Depends(get_db), _: User = Depends(_guard)
):
    goal = Goal(**payload.model_dump())
    db.add(goal)
    db.commit()
    db.refresh(goal)
    return goal
