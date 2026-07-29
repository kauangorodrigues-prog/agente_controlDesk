"""Setor Infraestrutura: incidentes e saúde dos sistemas."""
from __future__ import annotations

from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.deps import require_sector
from app.core.rbac import Sector
from app.models.infra import Incident, SystemHealthCheck
from app.models.user import User
from app.schemas.sectors import IncidentCreate, IncidentOut

router = APIRouter(prefix="/api/infraestrutura", tags=["Setor · Infraestrutura"])
_guard = require_sector(Sector.INFRAESTRUTURA)


@router.get("/incidents", response_model=list[IncidentOut])
def list_incidents(db: Session = Depends(get_db), _: User = Depends(_guard)):
    return db.scalars(select(Incident).order_by(Incident.opened_at.desc())).all()


@router.post("/incidents", response_model=IncidentOut, status_code=status.HTTP_201_CREATED)
def open_incident(
    payload: IncidentCreate, db: Session = Depends(get_db), _: User = Depends(_guard)
):
    incident = Incident(**payload.model_dump())
    db.add(incident)
    db.commit()
    db.refresh(incident)
    return incident


@router.post("/incidents/{incident_id}/resolve", response_model=IncidentOut)
def resolve_incident(
    incident_id: int, db: Session = Depends(get_db), _: User = Depends(_guard)
):
    incident = db.get(Incident, incident_id)
    if not incident:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Incidente não encontrado.")
    incident.status = "resolvido"
    incident.resolved_at = datetime.now(timezone.utc)
    db.commit()
    db.refresh(incident)
    return incident


@router.get("/health")
def infra_health(db: Session = Depends(get_db), _: User = Depends(_guard)):
    """Últimos health checks por serviço."""
    checks = db.scalars(
        select(SystemHealthCheck).order_by(SystemHealthCheck.checked_at.desc()).limit(50)
    ).all()
    open_incidents = db.scalar(
        select(Incident).where(Incident.status != "resolvido").limit(1)
    )
    return {
        "has_open_incidents": open_incidents is not None,
        "checks": [
            {
                "service": c.service,
                "status": c.status,
                "latency_ms": c.latency_ms,
                "cpu_pct": c.cpu_pct,
                "mem_pct": c.mem_pct,
                "checked_at": c.checked_at,
            }
            for c in checks
        ],
    }
