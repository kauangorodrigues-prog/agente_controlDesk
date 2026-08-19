"""Rate limiting persistente (serverless-safe) para proteção contra brute-force.

Usa o banco de dados como backend, funcionando corretamente mesmo em ambientes
serverless com múltiplas invocações isoladas (onde memória não persiste).
"""
from __future__ import annotations

from datetime import datetime, timedelta, timezone

from sqlalchemy import delete, func, select
from sqlalchemy.orm import Session

from app.models.login_attempt import LoginAttempt


def is_locked(db: Session, key: str, max_attempts: int, window_seconds: int) -> bool:
    """True se houve >= max_attempts falhas para a chave dentro da janela."""
    cutoff = datetime.now(timezone.utc) - timedelta(seconds=window_seconds)
    count = db.scalar(
        select(func.count(LoginAttempt.id)).where(
            LoginAttempt.key == key, LoginAttempt.created_at > cutoff
        )
    )
    return (count or 0) >= max_attempts


def record_failure(db: Session, key: str, window_seconds: int = 3600) -> None:
    """Registra uma falha e limpa tentativas antigas da mesma chave."""
    db.add(LoginAttempt(key=key))
    cutoff = datetime.now(timezone.utc) - timedelta(seconds=window_seconds)
    db.execute(
        delete(LoginAttempt).where(
            LoginAttempt.key == key, LoginAttempt.created_at <= cutoff
        )
    )
    db.commit()


def reset(db: Session, key: str) -> None:
    """Zera as tentativas após login bem-sucedido."""
    db.execute(delete(LoginAttempt).where(LoginAttempt.key == key))
    db.commit()
