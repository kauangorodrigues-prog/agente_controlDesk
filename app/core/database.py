"""Acesso a banco: engine (primária + réplica de leitura), pool, statement
timeout, sessão, e helpers de query/comando/dataframe.

Camada core: depende de `app.config` (CFG) e `app.core.resilience` (retry).
Não conhece as camadas superiores.
"""
from __future__ import annotations

from contextlib import contextmanager

import pandas as pd

from app.config import CFG
from app.core.resilience import retry_call


def _criar_engine(url: str = None):
    try:
        from sqlalchemy import create_engine
        from sqlalchemy.pool import QueuePool
        connect_args = {}
        if CFG.DB_STATEMENT_TIMEOUT_MS > 0:
            # Aborta consultas que passem do limite (evita queries presas).
            connect_args["options"] = f"-c statement_timeout={CFG.DB_STATEMENT_TIMEOUT_MS}"
        return create_engine(
            url or CFG.DATABASE_URL,
            poolclass=QueuePool,
            pool_size=CFG.POSTGRES_POOL_SIZE,
            max_overflow=CFG.POSTGRES_MAX_OVERFLOW,
            pool_timeout=30,
            pool_recycle=1800,
            pool_pre_ping=True,
            connect_args=connect_args,
            echo=(CFG.AMBIENTE == "development"),
        )
    except Exception as e:
        print(f"[DB] Engine não criado: {e}")
        return None


engine = _criar_engine()  # primária (leitura + escrita)
# Réplica de leitura opcional; sem DATABASE_REPLICA_URL usa a primária.
engine_leitura = _criar_engine(CFG.DATABASE_REPLICA_URL) if CFG.DATABASE_REPLICA_URL else engine


def _erros_transientes_db() -> tuple:
    try:
        from sqlalchemy.exc import OperationalError, InterfaceError, InternalError
        return (OperationalError, InterfaceError, InternalError)
    except Exception:
        return (Exception,)


@contextmanager
def get_db(leitura: bool = False):
    """Sessão SQLAlchemy. leitura=True usa a réplica (se configurada)."""
    from sqlalchemy.orm import sessionmaker
    eng = engine_leitura if leitura else engine
    if eng is None:
        raise RuntimeError("Banco de dados não configurado.")
    Session = sessionmaker(bind=eng)
    session = Session()
    try:
        yield session
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()


def executar_query(sql: str, params: dict = None) -> list:
    """Leitura (réplica se disponível) com retry em erros transientes de conexão."""
    from sqlalchemy import text

    def _exec():
        with get_db(leitura=True) as session:
            result = session.execute(text(sql), params or {})
            cols = result.keys()
            return [dict(zip(cols, row)) for row in result.fetchall()]

    if CFG.DB_READ_RETRY and CFG.DB_READ_RETRY > 0:
        # Só reexecuta em desconexão real; NUNCA em statement_timeout/erro de
        # consulta (reexecutar uma query lenta só amplia a carga).
        return retry_call(
            _exec, max_retries=CFG.DB_READ_RETRY, base_delay=0.5, max_delay=4.0,
            exceptions=_erros_transientes_db(), nome="db_read",
            retriavel=lambda e: bool(getattr(e, "connection_invalidated", False)),
        )
    return _exec()


def executar_comando(sql: str, params: dict = None) -> int:
    # Escrita na primária. Sem retry automático de propósito: reexecutar um
    # comando pode aplicá-lo duas vezes. pool_pre_ping trata conexões velhas.
    from sqlalchemy import text
    with get_db() as session:
        result = session.execute(text(sql), params or {})
        return result.rowcount


def ler_dataframe(sql: str, params: dict = None):
    """Lê um DataFrame pela réplica de leitura (offload de consultas pesadas)."""
    from sqlalchemy import text
    if engine_leitura is None:
        raise RuntimeError("Banco de dados não configurado.")
    with engine_leitura.connect() as conn:
        return pd.read_sql(text(sql), conn, params=params or {})


def testar_conexao(leitura: bool = False) -> bool:
    try:
        from sqlalchemy import text
        eng = engine_leitura if leitura else engine
        with eng.connect() as conn:
            conn.execute(text("SELECT 1"))
        return True
    except Exception:
        return False
