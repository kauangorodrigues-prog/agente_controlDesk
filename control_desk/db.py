from __future__ import annotations

from contextlib import contextmanager
from typing import Any, Iterator

from sqlalchemy import create_engine, text
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import QueuePool

from .config import CFG
from .logging_setup import get_logger

log = get_logger("db")


def _criar_engine() -> Engine | None:
    try:
        return create_engine(
            CFG.DATABASE_URL,
            poolclass=QueuePool,
            pool_size=5,
            max_overflow=10,
            pool_timeout=30,
            pool_recycle=1800,
            pool_pre_ping=True,
            echo=(CFG.AMBIENTE == "development"),
        )
    except Exception as e:
        log.error(f"Engine não criado: {e}")
        return None


engine = _criar_engine()
_Session = sessionmaker(bind=engine) if engine is not None else None


@contextmanager
def get_db() -> Iterator[Session]:
    """Context manager para sessão SQLAlchemy."""
    if _Session is None:
        raise RuntimeError("Banco de dados não configurado.")
    session = _Session()
    try:
        yield session
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()


def executar_query(sql: str, params: dict[str, Any] | None = None) -> list[dict]:
    with get_db() as session:
        result = session.execute(text(sql), params or {})
        cols = result.keys()
        return [dict(zip(cols, row)) for row in result.fetchall()]


def executar_comando(sql: str, params: dict[str, Any] | None = None) -> int:
    with get_db() as session:
        result = session.execute(text(sql), params or {})
        return result.rowcount


def testar_conexao() -> bool:
    if engine is None:
        return False
    try:
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
        return True
    except Exception:
        return False
