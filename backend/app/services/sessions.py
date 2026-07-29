"""Gerenciamento de sessões via refresh tokens revogáveis."""
from __future__ import annotations

import hashlib
import secrets
from datetime import datetime, timedelta, timezone

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import settings
from app.models.token import RefreshToken


def _hash(token: str) -> str:
    return hashlib.sha256(token.encode()).hexdigest()


def issue_refresh_token(
    db: Session, user_id: int, user_agent: str | None = None
) -> str:
    """Cria um refresh token opaco, persiste apenas o hash e retorna o valor."""
    raw = secrets.token_urlsafe(48)
    expires = datetime.now(timezone.utc) + timedelta(
        days=settings.REFRESH_TOKEN_EXPIRE_DAYS
    )
    db.add(
        RefreshToken(
            user_id=user_id,
            token_hash=_hash(raw),
            expires_at=expires,
            user_agent=(user_agent or "")[:200] or None,
        )
    )
    db.commit()
    return raw


def get_valid_token(db: Session, raw: str) -> RefreshToken | None:
    record = db.scalar(
        select(RefreshToken).where(RefreshToken.token_hash == _hash(raw))
    )
    if record and record.is_valid:
        return record
    return None


def revoke(db: Session, raw: str) -> bool:
    record = db.scalar(
        select(RefreshToken).where(RefreshToken.token_hash == _hash(raw))
    )
    if not record:
        return False
    record.revoked = True
    db.commit()
    return True


def revoke_all_for_user(db: Session, user_id: int) -> int:
    tokens = db.scalars(
        select(RefreshToken).where(
            RefreshToken.user_id == user_id, RefreshToken.revoked.is_(False)
        )
    ).all()
    for t in tokens:
        t.revoked = True
    db.commit()
    return len(tokens)


def rotate(db: Session, record: RefreshToken) -> str:
    """Revoga o token atual e emite um novo (rotação segura de refresh)."""
    record.revoked = True
    db.commit()
    return issue_refresh_token(db, record.user_id, record.user_agent)
