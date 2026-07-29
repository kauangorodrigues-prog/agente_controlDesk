"""Rotas da régua de comunicação (notificações ao titular)."""
from __future__ import annotations

from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, Request, status
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.deps import get_current_user
from app.models.debtor import Debtor
from app.models.notification import Notification
from app.models.user import User
from app.services import audit
from app.services.notifications import TEMPLATES, send_to_debtor

router = APIRouter(prefix="/api/notifications", tags=["Régua de Comunicação"])


class NotificationCreate(BaseModel):
    debtor_id: int
    template: str = Field(description="lembrete | proposta | acordo_confirmado")
    channel: str = Field(default="email", pattern="^(email|sms|whatsapp)$")


class NotificationOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    debtor_id: int
    channel: str
    template: str
    subject: str
    status: str
    created_at: datetime


@router.get("/templates")
def list_templates(_: User = Depends(get_current_user)):
    """Modelos de mensagem disponíveis na régua."""
    return [
        {"key": key, "subject": subject} for key, (subject, _body) in TEMPLATES.items()
    ]


@router.get("", response_model=list[NotificationOut])
def list_notifications(
    debtor_id: int | None = None,
    limit: int = 50,
    db: Session = Depends(get_db),
    _: User = Depends(get_current_user),
):
    stmt = select(Notification)
    if debtor_id:
        stmt = stmt.where(Notification.debtor_id == debtor_id)
    stmt = stmt.order_by(Notification.created_at.desc()).limit(min(limit, 200))
    return db.scalars(stmt).all()


@router.post("", response_model=NotificationOut, status_code=status.HTTP_201_CREATED)
def send_notification(
    payload: NotificationCreate,
    request: Request,
    db: Session = Depends(get_db),
    actor: User = Depends(get_current_user),
):
    if payload.template not in TEMPLATES:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Template inválido.")
    debtor = db.get(Debtor, payload.debtor_id)
    if not debtor:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Devedor não encontrado.")

    notification = send_to_debtor(db, debtor, payload.template, payload.channel)
    audit.record(db, action="notification.send", entity="notification",
                 entity_id=notification.id, actor=actor, request=request,
                 detail=f"{payload.template}/{notification.status}")
    return notification
