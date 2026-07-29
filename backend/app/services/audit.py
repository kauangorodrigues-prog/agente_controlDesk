"""Serviço de auditoria (accountability LGPD)."""
from __future__ import annotations

from typing import Optional

from fastapi import Request
from sqlalchemy.orm import Session

from app.models.audit import AuditLog
from app.models.user import User


def record(
    db: Session,
    *,
    action: str,
    entity: str,
    entity_id: str | int | None = None,
    actor: Optional[User] = None,
    detail: str | None = None,
    request: Optional[Request] = None,
) -> AuditLog:
    """Grava um evento de auditoria. Faz commit imediato para durabilidade."""
    ip = None
    if request is not None and request.client:
        ip = request.client.host

    log = AuditLog(
        actor_id=actor.id if actor else None,
        actor_email=actor.email if actor else None,
        action=action,
        entity=entity,
        entity_id=str(entity_id) if entity_id is not None else None,
        detail=detail,
        ip_address=ip,
    )
    db.add(log)
    db.commit()
    db.refresh(log)
    return log
