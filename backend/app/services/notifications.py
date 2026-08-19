"""Serviço de notificações da régua de cobrança.

Envia comunicações ao titular (e-mail via SMTP) e registra cada envio para
auditoria e conformidade LGPD. Em desenvolvimento (sem SMTP configurado),
opera em modo "dry-run": registra a notificação sem enviar de fato.

A régua respeita o consentimento/base legal de comunicação do titular:
notificações de finalidade "comunicacao" só são enviadas se houver consentimento
ativo ou base legal compatível.
"""
from __future__ import annotations

import logging
import smtplib
from email.mime.text import MIMEText

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import settings
from app.models.debtor import Debtor
from app.models.lgpd import ConsentRecord
from app.models.notification import Notification

logger = logging.getLogger("controldesk.notifications")

# Modelos de mensagem da régua (templates simples).
TEMPLATES: dict[str, tuple[str, str]] = {
    "lembrete": (
        "Lembrete sobre sua pendência",
        "Olá, {nome}. Identificamos uma pendência em aberto. "
        "Entre em contato para regularizar de forma facilitada.",
    ),
    "proposta": (
        "Proposta de negociação",
        "Olá, {nome}. Temos uma proposta especial para quitação da sua "
        "pendência com condições diferenciadas. Fale conosco.",
    ),
    "acordo_confirmado": (
        "Acordo confirmado",
        "Olá, {nome}. Seu acordo foi registrado com sucesso. "
        "Fique atento(a) às datas de vencimento das parcelas.",
    ),
}


def _has_communication_basis(db: Session, debtor_id: int) -> bool:
    """Verifica se há base legal/consentimento para comunicação (LGPD)."""
    consent = db.scalar(
        select(ConsentRecord).where(
            ConsentRecord.debtor_id == debtor_id,
            ConsentRecord.granted.is_(True),
        )
    )
    return consent is not None


def _deliver_email(to: str, subject: str, body: str) -> str:
    """Envia e-mail via SMTP. Retorna o status do envio."""
    if not settings.SMTP_HOST:
        logger.info("[dry-run] E-mail para %s | %s", to, subject)
        return "simulado"

    msg = MIMEText(body, _charset="utf-8")
    msg["Subject"] = subject
    msg["From"] = settings.SMTP_FROM
    msg["To"] = to

    with smtplib.SMTP(settings.SMTP_HOST, settings.SMTP_PORT, timeout=10) as server:
        if settings.SMTP_USE_TLS:
            server.starttls()
        if settings.SMTP_USER:
            server.login(settings.SMTP_USER, settings.SMTP_PASSWORD)
        server.send_message(msg)
    return "enviado"


def send_to_debtor(
    db: Session,
    debtor: Debtor,
    template: str,
    channel: str = "email",
) -> Notification:
    """Dispara uma notificação da régua para o titular e registra o envio."""
    if template not in TEMPLATES:
        raise ValueError(f"Template desconhecido: {template}")

    subject, body_tmpl = TEMPLATES[template]
    body = body_tmpl.format(nome=debtor.full_name.split()[0])

    # Guardrails LGPD + dados de contato.
    if not _has_communication_basis(db, debtor.id):
        status = "bloqueado_lgpd"
    elif channel == "email" and not debtor.email:
        status = "sem_contato"
    else:
        try:
            status = _deliver_email(debtor.email or "", subject, body)
        except Exception as exc:  # pragma: no cover - falha de rede externa
            logger.warning("Falha ao enviar notificação: %s", exc)
            status = "falha"

    notification = Notification(
        debtor_id=debtor.id,
        channel=channel,
        template=template,
        subject=subject,
        status=status,
    )
    db.add(notification)
    db.commit()
    db.refresh(notification)
    return notification
