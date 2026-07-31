from __future__ import annotations

from datetime import date, datetime, time as dtime, timedelta

import pandas as pd

from .config import CFG
from .db import executar_comando, executar_query
from .logging_setup import get_logger

log = get_logger("holidays")


def _str_para_time(s: str) -> dtime:
    try:
        p = str(s).split(":")
        return dtime(int(p[0]), int(p[1]))
    except Exception:
        return dtime(8, 0)


class HolidayService:
    @staticmethod
    def _feriados_banco(data_alvo: date | None = None) -> pd.DataFrame:
        data_alvo = data_alvo or date.today()
        try:
            rows = executar_query(
                "SELECT * FROM feriados WHERE data = :d ORDER BY tipo",
                {"d": data_alvo.isoformat()},
            )
            return pd.DataFrame(rows)
        except Exception:
            return pd.DataFrame()

    @staticmethod
    def e_feriado(data_alvo: date | None = None, uf: str | None = None) -> tuple:
        data_alvo = data_alvo or date.today()
        if not CFG.PAUSAR_EM_FERIADOS:
            return False, ""
        df = HolidayService._feriados_banco(data_alvo)
        if df.empty:
            return False, ""
        for _, row in df.iterrows():
            tipo = row.get("tipo", "NACIONAL")
            if not row.get("pausar_discagem", True):
                continue
            if tipo == "NACIONAL":
                return True, row["nome"]
            if tipo == "ESTADUAL" and uf and str(row.get("uf", "")).upper() == uf.upper():
                return True, row["nome"]
            if tipo == "EMPRESA":
                return True, row["nome"]
        return False, ""

    @staticmethod
    def pausar_mailing_hoje(data_alvo: date | None = None) -> tuple:
        data_alvo = data_alvo or date.today()
        df = HolidayService._feriados_banco(data_alvo)
        if df.empty:
            return False, ""
        for _, row in df.iterrows():
            if row.get("pausar_mailing", True):
                return True, row["nome"]
        return False, ""

    @staticmethod
    def dentro_do_horario(campanha_id: str | None = None, agora: datetime | None = None) -> tuple:
        agora = agora or datetime.now()
        hora_atual = agora.time()
        dia_semana = agora.weekday()

        config = None
        if campanha_id:
            try:
                rows = executar_query(
                    "SELECT * FROM campaign_config WHERE campanha_id = :id AND ativo = TRUE",
                    {"id": campanha_id},
                )
                config = rows[0] if rows else None
            except Exception:
                pass

        if config:
            hora_ini = _str_para_time(str(config.get("hora_inicio", CFG.PACING_HORA_INICIO_GLOBAL)))
            hora_fim_s = _str_para_time(str(config.get("hora_fim", CFG.PACING_HORA_FIM_GLOBAL)))
            hora_fim_sa = _str_para_time(str(config.get("hora_fim_sabado", CFG.PACING_HORA_FIM_SABADO)))
            permite_dom = config.get("permitir_domingo", False)
        else:
            hora_ini = _str_para_time(CFG.PACING_HORA_INICIO_GLOBAL)
            hora_fim_s = _str_para_time(CFG.PACING_HORA_FIM_GLOBAL)
            hora_fim_sa = _str_para_time(CFG.PACING_HORA_FIM_SABADO)
            permite_dom = False

        if dia_semana == 6 and not permite_dom:
            return False, "Discagem bloqueada aos domingos"

        hora_fim = hora_fim_sa if dia_semana == 5 else hora_fim_s

        if hora_atual < hora_ini:
            return False, f"Antes do horário permitido (início: {hora_ini.strftime('%H:%M')})"
        if hora_atual >= hora_fim:
            return False, f"Após o horário permitido (fim: {hora_fim.strftime('%H:%M')})"

        return True, ""

    @staticmethod
    def pacing_permitido(campanha_id: str | None = None, uf: str | None = None, agora: datetime | None = None) -> tuple:
        agora = agora or datetime.now()
        e_fer, nome = HolidayService.e_feriado(agora.date(), uf=uf)
        if e_fer:
            return False, f"Feriado: {nome}"
        return HolidayService.dentro_do_horario(campanha_id, agora)

    @staticmethod
    def listar_feriados(ano: int | None = None) -> list:
        ano = ano or date.today().year
        try:
            return executar_query(
                "SELECT * FROM feriados WHERE EXTRACT(YEAR FROM data) = :ano ORDER BY data",
                {"ano": ano},
            )
        except Exception:
            return []

    @staticmethod
    def adicionar_feriado(
        data_f: date, nome: str, tipo: str = "EMPRESA",
        uf: str | None = None, municipio: str | None = None,
        pausar_mailing: bool = True, pausar_discagem: bool = True,
        pacing_especial: float | None = None, observacao: str | None = None,
        criado_por: str = "USUARIO",
    ) -> bool:
        try:
            executar_comando(
                """
                INSERT INTO feriados
                    (data, nome, tipo, uf, municipio, pausar_mailing,
                     pausar_discagem, pacing_especial, observacao, criado_por)
                VALUES (:data, :nome, :tipo, :uf, :municipio, :pm,
                        :pd, :pe, :obs, :criado)
                ON CONFLICT (data, tipo, uf, municipio) DO UPDATE
                    SET nome = EXCLUDED.nome,
                        pausar_mailing  = EXCLUDED.pausar_mailing,
                        pausar_discagem = EXCLUDED.pausar_discagem,
                        pacing_especial = EXCLUDED.pacing_especial,
                        observacao      = EXCLUDED.observacao
                """,
                {
                    "data": data_f.isoformat(), "nome": nome, "tipo": tipo.upper(),
                    "uf": uf, "municipio": municipio,
                    "pm": pausar_mailing, "pd": pausar_discagem,
                    "pe": pacing_especial, "obs": observacao, "criado": criado_por,
                },
            )
            log.info(f"Feriado adicionado: {data_f} — {nome}")
            return True
        except Exception as e:
            log.error(f"Erro ao adicionar feriado: {e}")
            return False

    @staticmethod
    def remover_feriado(feriado_id: int) -> bool:
        try:
            n = executar_comando("DELETE FROM feriados WHERE id = :id", {"id": feriado_id})
            return n > 0
        except Exception:
            return False

    @staticmethod
    def proximos_feriados(dias: int = 30) -> list:
        try:
            fim = date.today() + timedelta(days=dias)
            return executar_query(
                "SELECT * FROM feriados WHERE data BETWEEN :i AND :f ORDER BY data",
                {"i": date.today().isoformat(), "f": fim.isoformat()},
            )
        except Exception:
            return []

    @staticmethod
    def sincronizar_feriados_nacionais(ano: int | None = None) -> int:
        ano = ano or date.today().year
        inseridos = 0
        try:
            import holidays as hol_lib
            br = hol_lib.Brazil(years=ano)
            for data_f, nome in br.items():
                if HolidayService.adicionar_feriado(data_f, nome, "NACIONAL", criado_por="SISTEMA_AUTO"):
                    inseridos += 1
            log.info(f"{inseridos} feriados nacionais sincronizados para {ano}")
        except ImportError:
            log.warning("Biblioteca 'holidays' não instalada — pulei a sincronização.")
        return inseridos
