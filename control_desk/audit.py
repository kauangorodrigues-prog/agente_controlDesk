from __future__ import annotations

from datetime import datetime

import pandas as pd

from .alerts import ALERTAS
from .config import CFG
from .db import engine
from .logging_setup import get_logger

log = get_logger("audit")


class AuditService:
    @staticmethod
    def run_audit() -> dict:
        log.info("=== Auditoria Operacional ===")
        relatorio: dict = {}
        problemas: list[str] = []

        # Agentes improdutivos
        try:
            df = pd.read_sql(
                """
                SELECT a.nome, a.campanha,
                       ROUND(EXTRACT(EPOCH FROM (NOW()-a.login_em))/60) AS min_logado,
                       COALESCE(l.ligacoes,0) AS ligacoes_hoje
                FROM agents a
                LEFT JOIN (
                    SELECT agente_id, COUNT(*) AS ligacoes
                    FROM calls WHERE DATE(iniciada_em) = CURRENT_DATE GROUP BY agente_id
                ) l ON a.agente_id = l.agente_id
                WHERE a.captured_at >= NOW() - INTERVAL '5 minutes'
                  AND LOWER(a.status) NOT IN ('paused', 'offline')
                  AND EXTRACT(EPOCH FROM (NOW()-a.login_em))/60 > 30
                  AND COALESCE(l.ligacoes, 0) = 0
                """,
                engine,
            )
            relatorio["agentes_improdutivos"] = len(df)
            if not df.empty:
                nomes = ", ".join(df["nome"].tolist()[:5])
                problemas.append(f"👤 *{len(df)} agente(s) sem produção*: {nomes}")
        except Exception as e:
            log.error(f"Improdutivos: {e}")

        # Campanhas paradas
        try:
            df = pd.read_sql(
                """
                SELECT s.campanha_id, s.campanha,
                       ROUND(EXTRACT(EPOCH FROM (NOW()-MAX(c.iniciada_em)))/60) AS min_parada
                FROM campaign_snapshot s
                LEFT JOIN calls c ON c.campanha_id = s.campanha_id
                WHERE s.captured_at >= NOW() - INTERVAL '10 minutes'
                  AND UPPER(s.status) = 'ACTIVE'
                GROUP BY s.campanha_id, s.campanha
                HAVING MAX(c.iniciada_em) < NOW() - INTERVAL '15 minutes' OR MAX(c.iniciada_em) IS NULL
                """,
                engine,
            )
            relatorio["campanhas_paradas"] = len(df)
            if not df.empty:
                problemas.append(f"📵 *{len(df)} campanha(s) parada(s)*: {', '.join(df['campanha'].tolist())}")
        except Exception as e:
            log.error(f"Campanhas paradas: {e}")

        # Mailing crítico
        try:
            df = pd.read_sql(
                """
                SELECT DISTINCT ON (campanha_id) campanha_id, campanha, mailing_restante_pct
                FROM mailing_status
                WHERE captured_at >= NOW() - INTERVAL '10 minutes'
                  AND mailing_restante_pct < :limite
                ORDER BY campanha_id, captured_at DESC
                """,
                engine,
                params={"limite": CFG.LIMITE_MAILING_RESTANTE},
            )
            relatorio["mailing_critico"] = len(df)
            for _, r in df.iterrows():
                problemas.append(f"🔴 Mailing *{r['campanha']}*: apenas *{r['mailing_restante_pct']:.1f}%*")
        except Exception as e:
            log.error(f"Mailing crítico: {e}")

        if problemas:
            ALERTAS.enviar_teams(
                "*AUDITORIA " + datetime.now().strftime("%H:%M") + "*\n\n" + "\n\n".join(problemas),
                nivel="ATENCAO", chave="auditoria", throttle_seg=1800,
            )

        relatorio["ts"] = datetime.utcnow().isoformat()
        return relatorio
