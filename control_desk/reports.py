from __future__ import annotations

import os
from datetime import date, datetime

import pandas as pd

from .alerts import ALERTAS
from .config import CFG
from .db import engine
from .logging_setup import get_logger

log = get_logger("reports")


class ReportService:
    @staticmethod
    def gerar_intraday() -> pd.DataFrame:
        try:
            return pd.read_sql(
                """
                SELECT campanha,
                       COUNT(*) AS acionamentos,
                       SUM(CASE WHEN tipo_resultado='CPC' THEN 1 ELSE 0 END) AS cpcs,
                       SUM(CASE WHEN tipo_resultado='RPC' THEN 1 ELSE 0 END) AS rpcs,
                       ROUND(AVG(ociosidade_pct),1) AS ociosidade_media,
                       MIN(mailing_restante_pct) AS mailing_restante
                FROM campaign_snapshot
                WHERE DATE(captured_at) = CURRENT_DATE
                GROUP BY campanha ORDER BY acionamentos DESC
                """,
                engine,
            )
        except Exception as e:
            log.error(f"Erro ao carregar intraday: {e}")
            return pd.DataFrame()

    @staticmethod
    def gerar_timeline() -> pd.DataFrame:
        """Evolução hora-a-hora do dia, para identificar períodos críticos."""
        try:
            return pd.read_sql(
                """
                SELECT DATE_TRUNC('hour', captured_at) AS hora,
                       campanha,
                       ROUND(AVG(ociosidade_pct), 1) AS ociosidade,
                       ROUND(AVG(abandono_pct), 1)   AS abandono,
                       MIN(mailing_restante_pct)     AS mailing_restante,
                       COUNT(*)                      AS snapshots
                FROM campaign_snapshot
                WHERE DATE(captured_at) = CURRENT_DATE
                GROUP BY 1, 2 ORDER BY 1, 2
                """,
                engine,
            )
        except Exception as e:
            log.error(f"Erro ao carregar timeline: {e}")
            return pd.DataFrame()

    @staticmethod
    def gerar_producao_operador() -> pd.DataFrame:
        try:
            return pd.read_sql(
                """
                SELECT a.nome AS operador, a.campanha,
                       COUNT(c.call_id) AS ligacoes,
                       SUM(CASE WHEN c.tipo_resultado IN ('CPC', 'RPC') THEN 1 ELSE 0 END) AS cpcs,
                       ROUND(AVG(c.duracao_seg) / 60, 1) AS tma_min
                FROM agents a
                LEFT JOIN calls c
                    ON c.agente_id = a.agente_id
                   AND DATE(c.iniciada_em) = CURRENT_DATE
                WHERE DATE(a.captured_at) = CURRENT_DATE
                GROUP BY a.nome, a.campanha ORDER BY ligacoes DESC
                """,
                engine,
            )
        except Exception as e:
            log.error(f"Erro ao carregar produção por operador: {e}")
            return pd.DataFrame()

    @staticmethod
    def exportar_excel(nome: str, sheets: dict[str, pd.DataFrame]) -> str:
        os.makedirs(CFG.DIR_REPORTS, exist_ok=True)
        caminho = os.path.join(CFG.DIR_REPORTS, nome)
        with pd.ExcelWriter(caminho, engine="openpyxl") as w:
            for aba, df in sheets.items():
                df.to_excel(w, sheet_name=aba, index=False)
        log.info(f"Excel gerado: {caminho}")
        return caminho

    @staticmethod
    def pipeline_intraday() -> None:
        log.info("Gerando relatório intraday...")
        df_intra = ReportService.gerar_intraday()
        df_timeline = ReportService.gerar_timeline()
        df_prod = ReportService.gerar_producao_operador()

        if df_intra.empty:
            log.warning("Intraday: sem dados no banco.")
            return

        nome = f"intraday_{date.today()}_{datetime.now().strftime('%H%M')}.xlsx"
        arquivo = ReportService.exportar_excel(
            nome, {"Campanhas": df_intra, "Operadores": df_prod, "Timeline": df_timeline}
        )

        total_a = int(df_intra["acionamentos"].sum())
        total_c = int(df_intra["cpcs"].sum())
        taxa = round(total_c / total_a * 100, 1) if total_a else 0.0
        ALERTAS.enviar_teams(
            f"*Intraday {datetime.now().strftime('%H:%M')}*\n"
            f"Acionamentos: *{total_a:,}* | CPCs: *{total_c:,}* ({taxa}%)\n"
            f"Campanhas: *{len(df_intra)}*",
            nivel="INFO", chave="relatorio_intraday", forcar=True,
        )
        ALERTAS.enviar_email(
            assunto=f"[Control Desk] Intraday {date.today()}",
            corpo=df_intra.to_html(index=False, border=0),
            anexo_path=arquivo,
        )
