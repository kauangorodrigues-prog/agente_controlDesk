"""Refresh tokens revogáveis (sessões de usuário).

O access token (JWT) é curto e stateless. O refresh token é opaco, tem vida
longa e é armazenado apenas como hash — permitindo revogação real no logout
ou em caso de comprometimento.
"""
from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy import Boolean, DateTime, ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


class RefreshToken(Base):
    __tablename__ = "refresh_tokens"

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), index=True, nullable=False
    )
    # Guarda apenas o hash SHA-256 do token (nunca o valor em claro).
    token_hash: Mapped[str] = mapped_column(String(64), unique=True, index=True)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    revoked: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )
    user_agent: Mapped[str | None] = mapped_column(String(200))

    @property
    def is_valid(self) -> bool:
        expires = self.expires_at
        # SQLite devolve datetime "naive"; assume UTC para comparação segura.
        if expires.tzinfo is None:
            expires = expires.replace(tzinfo=timezone.utc)
        return (not self.revoked) and expires > datetime.now(timezone.utc)
