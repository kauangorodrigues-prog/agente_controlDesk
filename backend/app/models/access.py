"""Acesso de um usuário a um setor específico da SaaS."""
from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy import DateTime, ForeignKey, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base


class SectorAccess(Base):
    __tablename__ = "sector_accesses"
    __table_args__ = (
        UniqueConstraint("user_id", "sector", name="uq_user_sector"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), index=True, nullable=False
    )
    # control_desk | planejamento | mis | desenvolvimento | infraestrutura
    sector: Mapped[str] = mapped_column(String(40), nullable=False)
    granted_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )

    user: Mapped["User"] = relationship(back_populates="sector_accesses")
