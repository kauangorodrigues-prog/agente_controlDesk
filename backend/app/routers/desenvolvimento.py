"""Setor Desenvolvimento: gestão de features e deploys."""
from __future__ import annotations

from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.deps import require_sector
from app.core.rbac import Sector
from app.models.devops import Deployment, Feature
from app.models.user import User
from app.schemas.sectors import FeatureCreate, FeatureOut

router = APIRouter(prefix="/api/desenvolvimento", tags=["Setor · Desenvolvimento"])
_guard = require_sector(Sector.DESENVOLVIMENTO)

_VALID_STATUS = {"backlog", "em_andamento", "review", "concluido"}


@router.get("/features", response_model=list[FeatureOut])
def list_features(db: Session = Depends(get_db), _: User = Depends(_guard)):
    return db.scalars(select(Feature).order_by(Feature.created_at.desc())).all()


@router.post("/features", response_model=FeatureOut, status_code=status.HTTP_201_CREATED)
def create_feature(
    payload: FeatureCreate, db: Session = Depends(get_db), _: User = Depends(_guard)
):
    feature = Feature(**payload.model_dump())
    db.add(feature)
    db.commit()
    db.refresh(feature)
    return feature


@router.patch("/features/{feature_id}/status", response_model=FeatureOut)
def move_feature(
    feature_id: int,
    new_status: str,
    db: Session = Depends(get_db),
    _: User = Depends(_guard),
):
    if new_status not in _VALID_STATUS:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, f"Status inválido: {new_status}")
    feature = db.get(Feature, feature_id)
    if not feature:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Feature não encontrada.")
    feature.status = new_status
    db.commit()
    db.refresh(feature)
    return feature


@router.get("/deployments")
def list_deployments(db: Session = Depends(get_db), _: User = Depends(_guard)):
    deps = db.scalars(select(Deployment).order_by(Deployment.deployed_at.desc())).all()
    return [
        {
            "id": d.id,
            "version": d.version,
            "environment": d.environment,
            "status": d.status,
            "deployed_at": d.deployed_at,
        }
        for d in deps
    ]


@router.post("/deployments", status_code=status.HTTP_201_CREATED)
def create_deployment(
    version: str,
    environment: str = "staging",
    notes: str | None = None,
    db: Session = Depends(get_db),
    _: User = Depends(_guard),
):
    dep = Deployment(
        version=version, environment=environment, status="sucesso",
        notes=notes, deployed_at=datetime.now(timezone.utc),
    )
    db.add(dep)
    db.commit()
    db.refresh(dep)
    return {"id": dep.id, "version": dep.version, "status": dep.status}
