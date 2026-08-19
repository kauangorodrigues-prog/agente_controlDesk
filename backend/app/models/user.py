"""Modelo de Usuário do sistema (colaboradores: diretoria, gerência, admin)."""
from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy import Boolean, DateTime, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(primary_key=True)
    full_name: Mapped[str] = mapped_column(String(180), nullable=False)
    email: Mapped[str] = mapped_column(String(180), unique=True, index=True, nullable=False)
    hashed_password: Mapped[str] = mapped_column(String(255), nullable=False)

    # Papel/cargo: diretoria | gerencia | administracao
    role: Mapped[str] = mapped_column(String(30), nullable=False, default="administracao")

    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    # Aceite dos termos de tratamento de dados (LGPD) para colaboradores.
    accepted_terms_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    last_login_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=_utcnow, onupdate=_utcnow
    )

    sector_accesses: Mapped[list["SectorAccess"]] = relationship(
        back_populates="user", cascade="all, delete-orphan"
    )
