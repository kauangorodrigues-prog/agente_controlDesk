"""Setor Control Desk: campanhas, pacing e monitoramento operacional."""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.deps import require_sector
from app.core.rbac import Sector
from app.models.control_desk import Campaign, PacingSnapshot
from app.models.user import User
from app.schemas.sectors import CampaignCreate, CampaignOut
from app.services import audit

router = APIRouter(prefix="/api/control-desk", tags=["Setor · Control Desk"])
_guard = require_sector(Sector.CONTROL_DESK)


@router.get("/campaigns", response_model=list[CampaignOut])
def list_campaigns(db: Session = Depends(get_db), _: User = Depends(_guard)):
    return db.scalars(select(Campaign).order_by(Campaign.name)).all()


@router.post("/campaigns", response_model=CampaignOut, status_code=status.HTTP_201_CREATED)
def create_campaign(
    payload: CampaignCreate,
    request: Request,
    db: Session = Depends(get_db),
    actor: User = Depends(_guard),
):
    campaign = Campaign(**payload.model_dump())
    db.add(campaign)
    db.commit()
    db.refresh(campaign)
    audit.record(db, action="campaign.create", entity="campaign", entity_id=campaign.id,
                 actor=actor, request=request)
    return campaign


@router.post("/campaigns/{campaign_id}/pacing")
def adjust_pacing(
    campaign_id: int,
    pacing: float,
    db: Session = Depends(get_db),
    actor: User = Depends(_guard),
):
    if not 1.0 <= pacing <= 8.0:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Pacing deve estar entre 1.0 e 8.0.")
    campaign = db.get(Campaign, campaign_id)
    if not campaign:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Campanha não encontrada.")
    campaign.pacing = pacing
    db.commit()
    return {"campaign_id": campaign_id, "pacing": pacing}


@router.get("/monitor")
def monitor(db: Session = Depends(get_db), _: User = Depends(_guard)):
    """Visão em tempo real consolidada das campanhas ativas."""
    campaigns = db.scalars(select(Campaign).where(Campaign.is_active.is_(True))).all()
    total_agents = sum(c.agents_online for c in campaigns)
    total_mailing = sum(c.mailing_total for c in campaigns)
    worked = sum(c.mailing_worked for c in campaigns)
    penetration = round((worked / total_mailing * 100), 1) if total_mailing else 0.0
    return {
        "campaigns_active": len(campaigns),
        "agents_online": total_agents,
        "mailing_total": total_mailing,
        "mailing_penetration_pct": penetration,
        "campaigns": [
            {
                "id": c.id,
                "name": c.name,
                "portfolio": c.portfolio,
                "pacing": c.pacing,
                "agents_online": c.agents_online,
            }
            for c in campaigns
        ],
    }


@router.post("/snapshots")
def create_snapshot(
    campaign_id: int,
    idle_pct: float = 0.0,
    abandon_pct: float = 0.0,
    calls_made: int = 0,
    contacts: int = 0,
    promises: int = 0,
    db: Session = Depends(get_db),
    _: User = Depends(_guard),
):
    snap = PacingSnapshot(
        campaign_id=campaign_id,
        idle_pct=idle_pct,
        abandon_pct=abandon_pct,
        calls_made=calls_made,
        contacts=contacts,
        promises=promises,
    )
    db.add(snap)
    db.commit()
    db.refresh(snap)
    # Alerta simples de guardrail (abandono acima de 8% é violação Anatel/boas práticas)
    alert = "abandono_alto" if abandon_pct > 8.0 else None
    return {"id": snap.id, "alert": alert}
