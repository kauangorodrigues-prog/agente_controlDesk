"""Serviço de análise ALO / NÃO ALO integrado aos conectores e ao banco.

Faz a ponte entre o discador (Olos), o analisador
(:mod:`control_desk.alo_analyzer`) e a persistência:

- **mapeia** registros de CDR/transcrição do Olos em :class:`Ligacao`;
- **analisa** cada ligação (IA ou heurística, com fallback automático);
- **persiste** o resultado na tabela ``alo_analises``;
- **agrega** estatísticas (por classificação e por operadora).

Todas as operações de banco são defensivas: sem banco configurado, a análise
em lote ainda roda e devolve os resultados (apenas não persiste).
"""
from __future__ import annotations

import json
from datetime import date, datetime, timedelta
from typing import Any, Optional

from .alo_analyzer import ANALISADOR, AnaliseResultado, Ligacao, Turno
from .clients import OlosClient
from .db import engine, executar_comando, executar_query
from .logging_setup import get_logger

log = get_logger("alo_service")


def _first(d: dict, *chaves: str, default: Any = None) -> Any:
    """Primeiro valor não-nulo entre variações de nome de campo."""
    for k in chaves:
        if k in d and d[k] not in (None, ""):
            return d[k]
    return default


def _num(v: Any, default: float = 0.0) -> float:
    try:
        return float(v)
    except (TypeError, ValueError):
        return default


def _mapear_turnos(raw: Any) -> list[Turno]:
    """Converte a transcrição estruturada do Olos em turnos.

    Aceita lista de dicts com variações de nome (``speaker``/``falante``,
    ``text``/``texto``, ``start``/``inicio_seg``/``offset``).
    """
    if not isinstance(raw, list):
        return []
    turnos: list[Turno] = []
    for item in raw:
        if not isinstance(item, dict):
            continue
        inicio = _first(item, "inicio_seg", "start", "start_seg", "offset", "ts")
        turnos.append(
            Turno(
                falante=str(_first(item, "falante", "speaker", "role", default="cliente")),
                texto=str(_first(item, "texto", "text", "transcript", default="")),
                inicio_seg=_num(inicio) if inicio is not None else None,
            )
        )
    return turnos


def mapear_ligacao(raw: dict) -> tuple[str, Ligacao]:
    """Mapeia um registro de chamada do Olos em ``(call_id, Ligacao)``.

    Tolera nomes de campo variados entre versões da API do discador.
    """
    call_id = str(_first(raw, "call_id", "id", "uuid", "callid", default=""))
    turnos_raw = _first(raw, "turnos", "turns", "transcription", "segments", default=None)
    lig = Ligacao(
        numero_chamado=str(_first(raw, "numero_chamado", "phone", "telefone", "to", "msisdn", default="")),
        numero_origem=str(_first(raw, "numero_origem", "from", "caller_id", "origem", default="")),
        data=str(_first(raw, "data", "date", "iniciada_em", "start_time", default="")),
        hora=str(_first(raw, "hora", "time", default="")),
        operadora=str(_first(raw, "operadora", "carrier", "operator", "trunk", default="")),
        duracao_total_seg=_num(_first(raw, "duracao_total_seg", "duration", "duracao", "billsec")),
        tempo_ate_conexao_seg=_num(_first(raw, "tempo_ate_conexao_seg", "connect_time", "ring_time", "pdd")),
        tempo_fala_seg=_num(_first(raw, "tempo_fala_seg", "talk_time", "tempo_fala")),
        tempo_silencio_seg=_num(_first(raw, "tempo_silencio_seg", "silence_time", "silencio")),
        tempo_espera_seg=_num(_first(raw, "tempo_espera_seg", "wait_time", "hold_time")),
        tempo_transferencia_seg=_num(_first(raw, "tempo_transferencia_seg", "transfer_time")),
        codigo_encerramento=str(_first(raw, "codigo_encerramento", "hangup_cause", "disposition", "status", default="")),
        causa_sip=str(_first(raw, "causa_sip", "sip_cause", "sip_code", "q850", default="")),
        amd=str(_first(raw, "amd", "amd_result", "cpa", "detection", default="")),
        transferencia=bool(_first(raw, "transferencia", "transferred", "was_transferred", default=False)),
        transcricao=str(_first(raw, "transcricao_texto", "transcript_text", default=""))
        if not isinstance(turnos_raw, list) else "",
    )
    tempo_alo = _first(raw, "tempo_ate_primeiro_alo_seg", "first_hello_time", "alo_time")
    if tempo_alo is not None:
        lig.tempo_ate_primeiro_alo_seg = _num(tempo_alo)
    lig.turnos = _mapear_turnos(turnos_raw)
    return call_id, lig


# ── Persistência ────────────────────────────────────────────────────────────
_DDL = """
CREATE TABLE IF NOT EXISTS alo_analises (
    id                    BIGSERIAL PRIMARY KEY,
    call_id               TEXT,
    numero_chamado        TEXT,
    operadora             TEXT,
    data_ligacao          TEXT,
    houve_alo             BOOLEAN,
    classificacao         TEXT,
    grau_confianca        INTEGER,
    quem_desligou         TEXT,
    houve_atraso          BOOLEAN,
    tempo_atraso_seg      NUMERIC,
    atraso_prejudicou     TEXT,
    operadora_entregou    TEXT,
    indicios_falha        TEXT,
    prob_falha_operadora  INTEGER,
    prob_falha_discador   INTEGER,
    prob_falha_agente     INTEGER,
    score_final           INTEGER,
    falso_positivo_alo    BOOLEAN,
    falso_negativo_alo    BOOLEAN,
    justificativa         TEXT,
    recomendacoes         TEXT,
    origem                TEXT,
    resultado             JSONB,
    analisado_em          TIMESTAMP DEFAULT NOW()
)
"""

_tabela_pronta = False


def _garantir_tabela() -> bool:
    global _tabela_pronta
    if engine is None:
        return False
    if _tabela_pronta:
        return True
    try:
        executar_comando(_DDL)
        _tabela_pronta = True
        return True
    except Exception as e:
        log.error(f"Não foi possível criar 'alo_analises': {e}")
        return False


def _persistir(call_id: str, lig: Ligacao, r: AnaliseResultado) -> bool:
    if not _garantir_tabela():
        return False
    sql = """
        INSERT INTO alo_analises (
            call_id, numero_chamado, operadora, data_ligacao, houve_alo,
            classificacao, grau_confianca, quem_desligou, houve_atraso,
            tempo_atraso_seg, atraso_prejudicou, operadora_entregou,
            indicios_falha, prob_falha_operadora, prob_falha_discador,
            prob_falha_agente, score_final, falso_positivo_alo,
            falso_negativo_alo, justificativa, recomendacoes, origem, resultado
        ) VALUES (
            :call_id, :numero_chamado, :operadora, :data_ligacao, :houve_alo,
            :classificacao, :grau_confianca, :quem_desligou, :houve_atraso,
            :tempo_atraso_seg, :atraso_prejudicou, :operadora_entregou,
            :indicios_falha, :prob_falha_operadora, :prob_falha_discador,
            :prob_falha_agente, :score_final, :falso_positivo_alo,
            :falso_negativo_alo, :justificativa, :recomendacoes, :origem,
            CAST(:resultado AS JSONB)
        )
    """
    try:
        executar_comando(sql, {
            "call_id": call_id,
            "numero_chamado": lig.numero_chamado,
            "operadora": lig.operadora,
            "data_ligacao": lig.data,
            "houve_alo": r.houve_alo,
            "classificacao": r.classificacao,
            "grau_confianca": r.grau_confianca,
            "quem_desligou": r.quem_desligou,
            "houve_atraso": r.houve_atraso,
            "tempo_atraso_seg": r.tempo_atraso_seg,
            "atraso_prejudicou": r.atraso_prejudicou,
            "operadora_entregou": r.operadora_entregou,
            "indicios_falha": ", ".join(r.indicios_falha),
            "prob_falha_operadora": r.prob_falha_operadora,
            "prob_falha_discador": r.prob_falha_discador,
            "prob_falha_agente": r.prob_falha_agente,
            "score_final": r.score_final,
            "falso_positivo_alo": r.falso_positivo_alo,
            "falso_negativo_alo": r.falso_negativo_alo,
            "justificativa": r.justificativa,
            "recomendacoes": " | ".join(r.recomendacoes),
            "origem": r.origem,
            "resultado": json.dumps(r.to_dict(), ensure_ascii=False),
        })
        return True
    except Exception as e:
        log.error(f"Falha ao persistir análise ALO (call_id={call_id}): {e}")
        return False


# ── Serviço ─────────────────────────────────────────────────────────────────
class AloService:
    """Orquestra análise ALO a partir dos conectores + persistência."""

    @staticmethod
    def analisar_call(
        call_id: str, persistir: bool = True, usar_ia: Optional[bool] = None
    ) -> dict:
        """Puxa CDR + transcrição do Olos, analisa e (opcional) persiste."""
        raw = OlosClient.get_call(call_id) or {}
        transc = OlosClient.get_call_transcription(call_id) or {}
        if transc:
            raw = {**raw, **transc}
        raw.setdefault("call_id", call_id)
        cid, lig = mapear_ligacao(raw)
        cid = cid or call_id
        resultado = ANALISADOR.analisar(lig, usar_ia=usar_ia)
        if persistir:
            _persistir(cid, lig, resultado)
        out = resultado.to_dict()
        out["call_id"] = cid
        return out

    @staticmethod
    def processar_lote(
        desde: Optional[str] = None,
        limite: int = 200,
        persistir: bool = True,
        usar_ia: Optional[bool] = None,
    ) -> dict:
        """Analisa em lote as chamadas recentes do discador.

        ``desde`` no formato ISO (``YYYY-MM-DD``); padrão = ontem.
        """
        if desde is None:
            desde = (date.today() - timedelta(days=1)).isoformat()

        chamadas = OlosClient.get_calls_para_alo(desde=desde, limite=limite)
        resumo = {
            "processadas": 0,
            "persistidas": 0,
            "alo": 0,
            "nao_alo": 0,
            "falsos_positivos": 0,
            "falsos_negativos": 0,
            "por_classificacao": {},
            "desde": desde,
            "ts": datetime.utcnow().isoformat(),
        }
        for raw in chamadas:
            if not isinstance(raw, dict):
                continue
            cid, lig = mapear_ligacao(raw)
            r = ANALISADOR.analisar(lig, usar_ia=usar_ia)
            resumo["processadas"] += 1
            resumo["alo"] += int(r.houve_alo)
            resumo["nao_alo"] += int(not r.houve_alo)
            resumo["falsos_positivos"] += int(r.falso_positivo_alo)
            resumo["falsos_negativos"] += int(r.falso_negativo_alo)
            resumo["por_classificacao"][r.classificacao] = (
                resumo["por_classificacao"].get(r.classificacao, 0) + 1
            )
            if persistir and _persistir(cid, lig, r):
                resumo["persistidas"] += 1

        log.info(
            f"ALO lote: {resumo['processadas']} chamadas "
            f"({resumo['alo']} ALO / {resumo['nao_alo']} NÃO ALO) desde {desde}"
        )
        return resumo

    @staticmethod
    def historico(
        limite: int = 100,
        classificacao: Optional[str] = None,
        operadora: Optional[str] = None,
    ) -> list[dict]:
        if engine is None:
            return []
        if not _garantir_tabela():
            return []
        sql = "SELECT * FROM alo_analises WHERE 1=1"
        params: dict = {}
        if classificacao:
            sql += " AND classificacao = :cls"
            params["cls"] = classificacao
        if operadora:
            sql += " AND operadora = :op"
            params["op"] = operadora
        sql += " ORDER BY analisado_em DESC LIMIT :lim"
        params["lim"] = limite
        try:
            return executar_query(sql, params)
        except Exception as e:
            log.error(f"Erro ao ler histórico ALO: {e}")
            return []

    @staticmethod
    def estatisticas(dias: int = 1) -> dict:
        """Agrega qualidade das ligações por classificação e por operadora."""
        if engine is None or not _garantir_tabela():
            return {"disponivel": False, "motivo": "banco indisponível"}
        try:
            total = executar_query(
                "SELECT COUNT(*) AS n, "
                "AVG(score_final) AS score_medio, "
                "SUM(CASE WHEN houve_alo THEN 1 ELSE 0 END) AS alo, "
                "SUM(CASE WHEN houve_atraso THEN 1 ELSE 0 END) AS com_atraso, "
                "SUM(CASE WHEN falso_positivo_alo THEN 1 ELSE 0 END) AS falsos_positivos, "
                "SUM(CASE WHEN falso_negativo_alo THEN 1 ELSE 0 END) AS falsos_negativos "
                "FROM alo_analises WHERE analisado_em >= NOW() - make_interval(days => :d)",
                {"d": dias},
            )
            por_cls = executar_query(
                "SELECT classificacao, COUNT(*) AS n, ROUND(AVG(score_final)) AS score_medio "
                "FROM alo_analises WHERE analisado_em >= NOW() - make_interval(days => :d) "
                "GROUP BY classificacao ORDER BY n DESC",
                {"d": dias},
            )
            por_op = executar_query(
                "SELECT operadora, COUNT(*) AS n, ROUND(AVG(score_final)) AS score_medio, "
                "SUM(CASE WHEN operadora_entregou <> 'SIM' THEN 1 ELSE 0 END) AS entregas_ruins "
                "FROM alo_analises WHERE analisado_em >= NOW() - make_interval(days => :d) "
                "GROUP BY operadora ORDER BY n DESC",
                {"d": dias},
            )
            return {
                "disponivel": True,
                "dias": dias,
                "resumo": total[0] if total else {},
                "por_classificacao": por_cls,
                "por_operadora": por_op,
            }
        except Exception as e:
            log.error(f"Erro nas estatísticas ALO: {e}")
            return {"disponivel": False, "motivo": str(e)}
