"""Camada de acesso ao banco de dados (SQLAlchemy 2.x)."""
from __future__ import annotations

from collections.abc import Generator

from sqlalchemy import create_engine
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker

from app.core.config import settings

# SQLite precisa de check_same_thread=False para uso com FastAPI (threads).
connect_args = {"check_same_thread": False} if settings.is_sqlite else {}

engine = create_engine(
    settings.DATABASE_URL,
    connect_args=connect_args,
    pool_pre_ping=True,
    echo=False,
)

SessionLocal = sessionmaker(
    autocommit=False, autoflush=False, bind=engine, expire_on_commit=False
)


class Base(DeclarativeBase):
    """Base declarativa para todos os modelos ORM."""


def get_db() -> Generator[Session, None, None]:
    """Dependency do FastAPI: fornece uma sessão por request."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def init_db() -> None:
    """Cria todas as tabelas. Importa os modelos para registrá-los na metadata."""
    from app import models  # noqa: F401  (registra os modelos)

    Base.metadata.create_all(bind=engine)
