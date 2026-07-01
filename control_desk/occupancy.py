from __future__ import annotations

from datetime import datetime

import pandas as pd

from .alerts import ALERTAS
from .config import CFG
from .db import engine
from .logging_setup import get_logger

log = get_logger("occupancy")

STATUS_OCIOSO = {"available", "idle", "livre", "free", "disponivel"}
STATUS_PAUSA = {"paused", "pause", "break", "pausa"}
STATUS_LIGANDO = {"on_call", "oncall", "dialing", "talking", "em_ligacao"}


class OccupancyService:
    @staticmethod
    def _ler_agentes() -> pd.DataFrame:
        try:
            df = pd.read_sql(
                "SELECT * FROM agents WHERE captured_at >= NOW() - INTERVAL '6 minutes'", engine
            )
        except Exception as e:
            log.error(f"Falha ao ler agentes do banco: {e}")
            return pd.DataFrame()
        if not df.empty:
            df["status_norm"] = df["status"].astype(str).str.lower().str.strip()
        return df

    @staticmethod
    def calculate_occupancy() -> dict:
        df = OccupancyService._ler_agentes()

        if df.empty:
            log.warning("Sem agentes nos últimos 6 min.")
            return {
                "total": 0, "ociosos": 0, "em_pausa": 0, "em_ligacao": 0,
                "ocupacao_pct": 0.0, "ociosidade_pct": 0.0,
                "agentes_pausa_longa": [], "erro": "Sem agentes logados",
            }

        total = len(df)
        ociosos = int(df["status_norm"].isin(STATUS_OCIOSO).sum())
        em_pausa = int(df["status_norm"].isin(STATUS_PAUSA).sum())
        em_ligacao = int(df["status_norm"].isin(STATUS_LIGANDO).sum())
        ocupacao_pct = round(((total - ociosos) / total) * 100, 2)
        ociosidade_pct = round((ociosos / total) * 100, 2)

        agentes_pausa_longa = []
        if "pausa_inicio" in df.columns:
            agora = datetime.utcnow()
            df_p = df[df["status_norm"].isin(STATUS_PAUSA)].copy()
            df_p["pausa_inicio"] = pd.to_datetime(df_p["pausa_inicio"], errors="coerce")
            df_p = df_p.dropna(subset=["pausa_inicio"])
            df_p["min_pausa"] = (agora - df_p["pausa_inicio"].dt.tz_localize(None)).dt.total_seconds() / 60
            longos = df_p[df_p["min_pausa"] > CFG.LIMITE_PAUSA_MIN]
            agentes_pausa_longa = [
                {"nome": r.get("nome", "?"), "min_pausa": round(r["min_pausa"])}
                for _, r in longos.iterrows()
            ]

        metricas = {
            "total": total, "ociosos": ociosos, "em_pausa": em_pausa,
            "em_ligacao": em_ligacao, "ocupacao_pct": ocupacao_pct,
            "ociosidade_pct": ociosidade_pct,
            "agentes_pausa_longa": agentes_pausa_longa,
            "ts": datetime.utcnow().isoformat(),
        }

        if ociosidade_pct > CFG.LIMITE_OCIOSIDADE_PCT:
            ALERTAS.enviar_teams(
                f"Ociosidade em *{ociosidade_pct:.1f}%* (limite {CFG.LIMITE_OCIOSIDADE_PCT}%)\n"
                f"Ociosos: {ociosos}/{total}",
                nivel="ATENCAO", chave="ociosidade_alta",
            )

        if agentes_pausa_longa:
            nomes = ", ".join(a["nome"] for a in agentes_pausa_longa[:5])
            ALERTAS.enviar_teams(
                f"Agentes em pausa > {CFG.LIMITE_PAUSA_MIN} min: {nomes}",
                nivel="ATENCAO", chave="pausa_longa",
            )

        return metricas

    @staticmethod
    def por_campanha() -> pd.DataFrame:
        df = OccupancyService._ler_agentes()
        if df.empty or "campanha" not in df.columns:
            return pd.DataFrame()
        g = (
            df.groupby("campanha")
            .agg(
                total=("agente_id", "count"),
                ociosos=("status_norm", lambda x: x.isin(STATUS_OCIOSO).sum()),
                em_pausa=("status_norm", lambda x: x.isin(STATUS_PAUSA).sum()),
                em_ligacao=("status_norm", lambda x: x.isin(STATUS_LIGANDO).sum()),
            )
            .reset_index()
        )
        g["ociosidade_pct"] = (g["ociosos"] / g["total"] * 100).round(1)
        g["ocupacao_pct"] = ((g["total"] - g["ociosos"]) / g["total"] * 100).round(1)
        return g
