"""Modelos do setor Desenvolvimento: features e deploys."""
from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy import DateTime, String
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


class Feature(Base):
    __tablename__ = "features"

    id: Mapped[int] = mapped_column(primary_key=True)
    title: Mapped[str] = mapped_column(String(160), nullable=False)
    description: Mapped[str | None] = mapped_column(String(1000))
    # backlog | em_andamento | review | concluido
    status: Mapped[str] = mapped_column(String(15), default="backlog", index=True)
    priority: Mapped[str] = mapped_column(String(10), default="media")  # baixa|media|alta
    squad: Mapped[str] = mapped_column(String(60), default="plataforma")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=_utcnow, onupdate=_utcnow
    )


class Deployment(Base):
    __tablename__ = "deployments"

    id: Mapped[int] = mapped_column(primary_key=True)
    version: Mapped[str] = mapped_column(String(40), nullable=False)
    environment: Mapped[str] = mapped_column(String(20), default="staging")
    # sucesso | falha | rollback | em_andamento
    status: Mapped[str] = mapped_column(String(15), default="em_andamento")
    notes: Mapped[str | None] = mapped_column(String(500))
    deployed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow)
