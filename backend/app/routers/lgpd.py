"""Módulo LGPD — conformidade com a Lei 13.709/2018.

Cobre:
  * Registro e revogação de consentimento (arts. 7º e 8º)
  * Requisições de titulares / direitos (art. 18): acesso, correção,
    exclusão, portabilidade, anonimização e revogação
  * Exportação de dados (acesso e portabilidade)
  * Anonimização irreversível
  * Consulta à trilha de auditoria (art. 37 — accountability)
  * Aviso de privacidade público
"""
from __future__ import annotations

import re
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.crypto import blind_index
from app.core.database import get_db
from app.core.deps import get_current_user, require_role
from app.core.rbac import Role
from app.models.audit import AuditLog
from app.models.debtor import Debtor
from app.models.lgpd import ConsentRecord, DataSubjectRequest
from app.models.user import User
from app.schemas.lgpd import (
    CONSENT_BASES,
    REQUEST_TYPES,
    ConsentCreate,
    ConsentOut,
    DSRCreate,
    DSROut,
    DSRUpdate,
)
from app.services import audit
from app.services.lgpd import anonymize_debtor, export_debtor_data

router = APIRouter(prefix="/api/lgpd", tags=["LGPD & Privacidade"])


# ── Aviso de Privacidade (público) ───────────────────────────────────────
@router.get("/privacy-notice")
def privacy_notice():
    """Aviso de privacidade público — não requer autenticação."""
    return {
        "controlador": settings.DATA_CONTROLLER_NAME,
        "encarregado_dpo": settings.DPO_EMAIL,
        "finalidades": [
            "Recuperação de crédito e cobrança de dívidas",
            "Negociação e formalização de acordos",
            "Prevenção à fraude e análise de risco de crédito",
            "Cumprimento de obrigações legais e regulatórias",
        ],
        "bases_legais": sorted(CONSENT_BASES),
        "direitos_do_titular": sorted(REQUEST_TYPES),
        "retencao_dias": settings.LGPD_RETENTION_DAYS,
        "canal_de_solicitacoes": "POST /api/lgpd/requests",
    }


# ── Consentimento ────────────────────────────────────────────────────────
@router.post("/consents", response_model=ConsentOut, status_code=status.HTTP_201_CREATED)
def register_consent(
    payload: ConsentCreate,
    request: Request,
    db: Session = Depends(get_db),
    actor: User = Depends(get_current_user),
):
    if payload.legal_basis not in CONSENT_BASES:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Base legal inválida.")
    if not db.get(Debtor, payload.debtor_id):
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Titular não encontrado.")

    consent = ConsentRecord(**payload.model_dump())
    db.add(consent)
    db.commit()
    db.refresh(consent)
    audit.record(db, action="consent.register", entity="consent", entity_id=consent.id,
                 actor=actor, request=request, detail=payload.purpose)
    return consent


@router.post("/consents/{consent_id}/revoke", response_model=ConsentOut)
def revoke_consent(
    consent_id: int,
    request: Request,
    db: Session = Depends(get_db),
    actor: User = Depends(get_current_user),
):
    consent = db.get(ConsentRecord, consent_id)
    if not consent:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Consentimento não encontrado.")
    consent.granted = False
    consent.revoked_at = datetime.now(timezone.utc)
    db.commit()
    db.refresh(consent)
    audit.record(db, action="consent.revoke", entity="consent", entity_id=consent.id,
                 actor=actor, request=request)
    return consent


@router.get("/consents/{debtor_id}", response_model=list[ConsentOut])
def list_consents(
    debtor_id: int, db: Session = Depends(get_db), _: User = Depends(get_current_user)
):
    return db.scalars(
        select(ConsentRecord).where(ConsentRecord.debtor_id == debtor_id)
    ).all()


# ── Requisições de titulares (art. 18) ───────────────────────────────────
@router.post("/requests", response_model=DSROut, status_code=status.HTTP_201_CREATED)
def open_request(payload: DSRCreate, request: Request, db: Session = Depends(get_db)):
    """Abertura pública de requisição pelo próprio titular (sem login)."""
    if payload.request_type not in REQUEST_TYPES:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Tipo de requisição inválido.")

    document = re.sub(r"\D", "", payload.requester_document)
    debtor = db.scalar(
        select(Debtor).where(Debtor.document_hash == blind_index(document))
    )

    dsr = DataSubjectRequest(
        debtor_id=debtor.id if debtor else None,
        requester_document=document,
        request_type=payload.request_type,
        notes=payload.notes,
    )
    db.add(dsr)
    db.commit()
    db.refresh(dsr)
    audit.record(db, action="dsr.open", entity="dsr", entity_id=dsr.id,
                 request=request, detail=payload.request_type)
    return dsr


@router.get("/requests", response_model=list[DSROut])
def list_requests(
    db: Session = Depends(get_db), _: User = Depends(require_role(Role.ADMINISTRACAO))
):
    return db.scalars(
        select(DataSubjectRequest).order_by(DataSubjectRequest.created_at.desc())
    ).all()


@router.patch("/requests/{request_id}", response_model=DSROut)
def update_request(
    request_id: int,
    payload: DSRUpdate,
    request: Request,
    db: Session = Depends(get_db),
    actor: User = Depends(require_role(Role.ADMINISTRACAO)),
):
    dsr = db.get(DataSubjectRequest, request_id)
    if not dsr:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Requisição não encontrada.")
    dsr.status = payload.status
    if payload.notes is not None:
        dsr.notes = payload.notes
    dsr.handled_by = actor.id
    if payload.status in ("concluida", "recusada"):
        dsr.resolved_at = datetime.now(timezone.utc)
    db.commit()
    db.refresh(dsr)
    audit.record(db, action="dsr.update", entity="dsr", entity_id=dsr.id,
                 actor=actor, request=request, detail=payload.status)
    return dsr


# ── Exportação (acesso / portabilidade) ──────────────────────────────────
@router.get("/export/{debtor_id}")
def export_data(
    debtor_id: int,
    request: Request,
    db: Session = Depends(get_db),
    actor: User = Depends(require_role(Role.ADMINISTRACAO)),
):
    debtor = db.get(Debtor, debtor_id)
    if not debtor:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Titular não encontrado.")
    audit.record(db, action="lgpd.export", entity="debtor", entity_id=debtor.id,
                 actor=actor, request=request)
    return export_debtor_data(db, debtor)


# ── Anonimização (direito de exclusão) ───────────────────────────────────
@router.post("/anonymize/{debtor_id}")
def anonymize(
    debtor_id: int,
    request: Request,
    db: Session = Depends(get_db),
    actor: User = Depends(require_role(Role.GERENCIA)),
):
    debtor = db.get(Debtor, debtor_id)
    if not debtor:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Titular não encontrado.")
    if debtor.is_anonymized:
        raise HTTPException(status.HTTP_409_CONFLICT, "Titular já anonimizado.")
    anonymize_debtor(db, debtor)
    audit.record(db, action="lgpd.anonymize", entity="debtor", entity_id=debtor.id,
                 actor=actor, request=request)
    return {"debtor_id": debtor.id, "anonymized": True}


# ── Trilha de auditoria (accountability) ─────────────────────────────────
@router.get("/audit-logs")
def audit_logs(
    limit: int = 100,
    db: Session = Depends(get_db),
    _: User = Depends(require_role(Role.GERENCIA)),
):
    logs = db.scalars(
        select(AuditLog).order_by(AuditLog.created_at.desc()).limit(min(limit, 500))
    ).all()
    return [
        {
            "id": lg.id,
            "actor_email": lg.actor_email,
            "action": lg.action,
            "entity": lg.entity,
            "entity_id": lg.entity_id,
            "detail": lg.detail,
            "ip_address": lg.ip_address,
            "created_at": lg.created_at,
        }
        for lg in logs
    ]
