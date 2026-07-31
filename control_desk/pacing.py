from __future__ import annotations

from datetime import datetime

from .alerts import ALERTAS
from .clients import OlosClient
from .config import CFG
from .db import executar_comando, executar_query
from .holidays import HolidayService
from .logging_setup import get_logger

log = get_logger("pacing")


class PacingService:
    @staticmethod
    def _configs() -> dict:
        try:
            rows = executar_query("SELECT * FROM campaign_config WHERE ativo = TRUE")
            return {r["campanha_id"]: r for r in rows}
        except Exception:
            return {}

    @staticmethod
    def _campanhas_ativas() -> list:
        try:
            return executar_query(
                """
                SELECT DISTINCT ON (campanha_id)
                    campanha_id, campanha, pacing_atual,
                    mailing_restante_pct, ocupacao_pct, ociosidade_pct, abandono_pct
                FROM campaign_snapshot
                WHERE captured_at >= NOW() - INTERVAL '10 minutes'
                  AND status = 'ACTIVE'
                ORDER BY campanha_id, captured_at DESC
                """
            )
        except Exception:
            return []

    @staticmethod
    def _calcular_pacing(
        ocupacao_pct: float, abandono_pct: float,
        pacing_min: float, pacing_max: float,
    ) -> tuple:
        if abandono_pct > CFG.LIMITE_ABANDONO_PCT:
            novo = pacing_min + (pacing_max - pacing_min) * 0.3
            return round(min(max(novo, pacing_min), pacing_max), 1), "abandono_alto"
        ociosidade = 100 - ocupacao_pct
        fator = ociosidade / 100
        novo = pacing_min + (pacing_max - pacing_min) * fator
        return round(min(max(novo, pacing_min), pacing_max), 1), "ajuste_proporcional"

    @staticmethod
    def _log_auditoria(
        cid: str, cnome: str, pant: float, pnovo: float,
        motivo: str, ocup: float, bloqueado: bool = False, mbloq: str = "",
    ) -> None:
        try:
            executar_comando(
                """
                INSERT INTO pacing_audit_log
                    (campanha_id, campanha_nome, pacing_anterior, pacing_novo,
                     motivo, ocupacao_pct, bloqueado, motivo_bloqueio, ts)
                VALUES (:cid, :cnome, :pant, :pnovo, :motivo, :ocup, :bloq, :mbloq, NOW())
                """,
                {
                    "cid": cid, "cnome": cnome, "pant": pant, "pnovo": pnovo,
                    "motivo": motivo, "ocup": ocup, "bloq": bloqueado, "mbloq": mbloq,
                },
            )
        except Exception as e:
            log.debug(f"Falha ao registrar auditoria de pacing: {e}")

    @staticmethod
    def auto_adjust_pacing() -> dict:
        configs = PacingService._configs()
        campanhas = PacingService._campanhas_ativas()
        agora = datetime.now()
        resultado = {}

        for camp in campanhas:
            cid = camp["campanha_id"]
            cnome = camp.get("campanha", cid)
            cfg = configs.get(cid, {})
            uf = cfg.get("uf_restricao")

            pacing_min = float(cfg.get("pacing_min", CFG.PACING_MIN_GLOBAL))
            pacing_max = float(cfg.get("pacing_max", CFG.PACING_MAX_GLOBAL))
            pacing_at = float(camp.get("pacing_atual", 2.0))
            ocup_pct = float(camp.get("ocupacao_pct", 80.0))
            aband_pct = float(camp.get("abandono_pct", 0.0))

            # ── Guardrail: feriado / horário ──────────────
            permitido, motivo_bloq = HolidayService.pacing_permitido(cid, uf=uf, agora=agora)
            if not permitido:
                log.info(f"{cnome} BLOQUEADO: {motivo_bloq}")
                PacingService._log_auditoria(cid, cnome, pacing_at, 0, "bloqueado_guardrail", ocup_pct, True, motivo_bloq)
                resultado[cid] = {"status": "bloqueado", "motivo": motivo_bloq}
                continue

            # ── Guardrail: pausa total em feriado ─────────
            pausar, nome_fer = HolidayService.pausar_mailing_hoje()
            if pausar and cfg.get("pausar_feriados", True):
                try:
                    OlosClient.pause_campaign(cid, f"Feriado: {nome_fer}")
                except Exception:
                    pass
                ALERTAS.enviar_teams(
                    f"Campanha *{cnome}* pausada — {nome_fer}",
                    nivel="INFO", chave=f"pausa_feriado_{cid}", throttle_seg=3600,
                )
                PacingService._log_auditoria(cid, cnome, pacing_at, 0, "pausa_feriado", ocup_pct, True, f"Feriado: {nome_fer}")
                resultado[cid] = {"status": "pausado", "motivo": f"Feriado: {nome_fer}"}
                continue

            # ── Cálculo ────────────────────────────────────
            novo_pacing, motivo_calc = PacingService._calcular_pacing(ocup_pct, aband_pct, pacing_min, pacing_max)

            if abs(novo_pacing - pacing_at) < 0.5:
                resultado[cid] = {"status": "sem_alteracao", "pacing": pacing_at}
                continue

            try:
                OlosClient.update_pacing(cid, novo_pacing)
            except Exception as e:
                log.error(f"API falhou {cid}: {e}")
                resultado[cid] = {"status": "erro_api"}
                continue

            PacingService._log_auditoria(cid, cnome, pacing_at, novo_pacing, motivo_calc, ocup_pct)
            dir_seta = "↑" if novo_pacing > pacing_at else "↓"
            log.info(f"{cnome}: {pacing_at} → {novo_pacing} {dir_seta}")
            resultado[cid] = {"status": "ajustado", "pacing_anterior": pacing_at, "pacing_novo": novo_pacing}

        return resultado

    @staticmethod
    def retomar_pos_feriado() -> None:
        e_fer, _ = HolidayService.e_feriado()
        if e_fer:
            return
        try:
            rows = executar_query(
                """
                SELECT DISTINCT campanha_id, campanha_nome
                FROM pacing_audit_log
                WHERE motivo_bloqueio LIKE 'Feriado%'
                  AND DATE(ts) = CURRENT_DATE - 1
                """
            )
            for r in rows:
                OlosClient.resume_campaign(r["campanha_id"])
                log.info(f"Retomada pós-feriado: {r['campanha_nome']}")
        except Exception as e:
            log.error(f"Erro na retomada pós-feriado: {e}")
