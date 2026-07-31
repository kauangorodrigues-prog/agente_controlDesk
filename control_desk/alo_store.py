"""Persistência das análises ALO — Postgres em produção, SQLite como fallback.

Se o Postgres do Control Desk estiver configurado (``engine`` disponível), grava
lá. Caso contrário, cai automaticamente para um arquivo SQLite local
(``ALO_SQLITE_PATH``, padrão ``data/alo_analises.db``), deixando o robô
**100% funcional sem nenhuma infraestrutura externa** — ideal para testar na
operação antes de plugar o banco corporativo.
"""
from __future__ import annotations

import json
import os
import sqlite3
import threading
from typing import Any, Optional

from .db import engine, executar_comando, executar_query
from .logging_setup import get_logger

log = get_logger("alo_store")

# Colunas de dados (sem id/analisado_em, gerados pelo banco).
COLUNAS = [
    "call_id", "numero_chamado", "operadora", "data_ligacao", "houve_alo",
    "classificacao", "grau_confianca", "quem_desligou", "houve_atraso",
    "tempo_atraso_seg", "atraso_prejudicou", "operadora_entregou",
    "indicios_falha", "prob_falha_operadora", "prob_falha_discador",
    "prob_falha_agente", "score_final", "falso_positivo_alo",
    "falso_negativo_alo", "justificativa", "recomendacoes", "origem", "resultado",
]

_SQLITE_PATH = os.getenv("ALO_SQLITE_PATH", os.path.join("data", "alo_analises.db"))
_lock = threading.Lock()
_pronto = False
_backend_cache: Optional[str] = None


def _postgres_ok() -> bool:
    try:
        from .db import testar_conexao
        return testar_conexao()
    except Exception:
        return False


def backend() -> str:
    """'postgres' se houver engine e o banco responder; senão 'sqlite'.

    Decidido uma vez e memorizado — garante fallback automático para SQLite
    quando o Postgres não está configurado ou não está acessível.
    """
    global _backend_cache
    if _backend_cache is None:
        _backend_cache = "postgres" if (engine is not None and _postgres_ok()) else "sqlite"
        log.info(f"Persistência ALO: backend={_backend_cache}")
    return _backend_cache


def disponivel() -> bool:
    return _garantir()


# ── DDL ─────────────────────────────────────────────────────────────────────
_DDL_PG = """
CREATE TABLE IF NOT EXISTS alo_analises (
    id BIGSERIAL PRIMARY KEY, call_id TEXT, numero_chamado TEXT, operadora TEXT,
    data_ligacao TEXT, houve_alo BOOLEAN, classificacao TEXT, grau_confianca INTEGER,
    quem_desligou TEXT, houve_atraso BOOLEAN, tempo_atraso_seg NUMERIC,
    atraso_prejudicou TEXT, operadora_entregou TEXT, indicios_falha TEXT,
    prob_falha_operadora INTEGER, prob_falha_discador INTEGER, prob_falha_agente INTEGER,
    score_final INTEGER, falso_positivo_alo BOOLEAN, falso_negativo_alo BOOLEAN,
    justificativa TEXT, recomendacoes TEXT, origem TEXT, resultado JSONB,
    analisado_em TIMESTAMP DEFAULT NOW()
)
"""
_DDL_SQLITE = """
CREATE TABLE IF NOT EXISTS alo_analises (
    id INTEGER PRIMARY KEY AUTOINCREMENT, call_id TEXT, numero_chamado TEXT,
    operadora TEXT, data_ligacao TEXT, houve_alo INTEGER, classificacao TEXT,
    grau_confianca INTEGER, quem_desligou TEXT, houve_atraso INTEGER,
    tempo_atraso_seg REAL, atraso_prejudicou TEXT, operadora_entregou TEXT,
    indicios_falha TEXT, prob_falha_operadora INTEGER, prob_falha_discador INTEGER,
    prob_falha_agente INTEGER, score_final INTEGER, falso_positivo_alo INTEGER,
    falso_negativo_alo INTEGER, justificativa TEXT, recomendacoes TEXT, origem TEXT,
    resultado TEXT, analisado_em TEXT DEFAULT (datetime('now'))
)
"""


def _sqlite_conn() -> sqlite3.Connection:
    diretorio = os.path.dirname(_SQLITE_PATH)
    if diretorio:
        os.makedirs(diretorio, exist_ok=True)
    conn = sqlite3.connect(_SQLITE_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def _garantir() -> bool:
    global _pronto
    if _pronto:
        return True
    with _lock:
        if _pronto:
            return True
        try:
            if backend() == "postgres":
                executar_comando(_DDL_PG)
            else:
                with _sqlite_conn() as c:
                    c.execute(_DDL_SQLITE)
            _pronto = True
            log.info(f"Tabela alo_analises pronta (backend={backend()}).")
            return True
        except Exception as e:
            log.error(f"Não foi possível preparar alo_analises ({backend()}): {e}")
            return False


# ── Escrita ─────────────────────────────────────────────────────────────────
def persistir(row: dict) -> bool:
    if not _garantir():
        return False
    dados = {c: row.get(c) for c in COLUNAS}
    try:
        if backend() == "postgres":
            placeholders = [
                "CAST(:resultado AS JSONB)" if c == "resultado" else f":{c}"
                for c in COLUNAS
            ]
            sql = (
                f"INSERT INTO alo_analises ({', '.join(COLUNAS)}) "
                f"VALUES ({', '.join(placeholders)})"
            )
            executar_comando(sql, dados)
        else:
            marcadores = ", ".join(f":{c}" for c in COLUNAS)
            sql = f"INSERT INTO alo_analises ({', '.join(COLUNAS)}) VALUES ({marcadores})"
            # SQLite aceita bool como int; força para evitar surpresa de driver.
            for b in ("houve_alo", "houve_atraso", "falso_positivo_alo", "falso_negativo_alo"):
                dados[b] = int(bool(dados.get(b)))
            with _sqlite_conn() as c:
                c.execute(sql, dados)
        return True
    except Exception as e:
        log.error(f"Falha ao persistir análise ALO (call_id={row.get('call_id')}): {e}")
        return False


# ── Leitura ─────────────────────────────────────────────────────────────────
def historico(
    limite: int = 100,
    classificacao: Optional[str] = None,
    operadora: Optional[str] = None,
) -> list[dict]:
    if not _garantir():
        return []
    where = " WHERE 1=1"
    params: dict = {}
    if classificacao:
        where += " AND classificacao = :cls"
        params["cls"] = classificacao
    if operadora:
        where += " AND operadora = :op"
        params["op"] = operadora
    sql = f"SELECT * FROM alo_analises{where} ORDER BY analisado_em DESC LIMIT :lim"
    params["lim"] = int(limite)
    try:
        if backend() == "postgres":
            return executar_query(sql, params)
        with _sqlite_conn() as c:
            return [dict(r) for r in c.execute(sql, params).fetchall()]
    except Exception as e:
        log.error(f"Erro ao ler histórico ALO: {e}")
        return []


def estatisticas(dias: int = 1) -> dict:
    if not _garantir():
        return {"disponivel": False, "backend": backend(), "motivo": "persistência indisponível"}
    dias = int(dias)
    pg = backend() == "postgres"
    corte = "NOW() - make_interval(days => :d)" if pg else f"datetime('now','-{dias} days')"
    b = (lambda col: f"SUM(CASE WHEN {col} THEN 1 ELSE 0 END)") if pg else (lambda col: f"SUM({col})")
    params = {"d": dias} if pg else {}
    try:
        run = executar_query if pg else _sqlite_query
        resumo = run(
            f"SELECT COUNT(*) AS n, AVG(score_final) AS score_medio, "
            f"{b('houve_alo')} AS alo, {b('houve_atraso')} AS com_atraso, "
            f"{b('falso_positivo_alo')} AS falsos_positivos, "
            f"{b('falso_negativo_alo')} AS falsos_negativos "
            f"FROM alo_analises WHERE analisado_em >= {corte}",
            params,
        )
        por_cls = run(
            f"SELECT classificacao, COUNT(*) AS n, ROUND(AVG(score_final)) AS score_medio "
            f"FROM alo_analises WHERE analisado_em >= {corte} "
            f"GROUP BY classificacao ORDER BY n DESC",
            params,
        )
        por_op = run(
            f"SELECT operadora, COUNT(*) AS n, ROUND(AVG(score_final)) AS score_medio, "
            f"SUM(CASE WHEN operadora_entregou <> 'SIM' THEN 1 ELSE 0 END) AS entregas_ruins "
            f"FROM alo_analises WHERE analisado_em >= {corte} "
            f"GROUP BY operadora ORDER BY n DESC",
            params,
        )
        return {
            "disponivel": True, "backend": backend(), "dias": dias,
            "resumo": resumo[0] if resumo else {},
            "por_classificacao": por_cls, "por_operadora": por_op,
        }
    except Exception as e:
        log.error(f"Erro nas estatísticas ALO: {e}")
        return {"disponivel": False, "backend": backend(),
                "motivo": "erro ao consultar estatísticas"}


def _sqlite_query(sql: str, params: dict | None = None) -> list[dict]:
    with _sqlite_conn() as c:
        return [dict(r) for r in c.execute(sql, params or {}).fetchall()]
