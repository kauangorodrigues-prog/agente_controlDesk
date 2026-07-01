from __future__ import annotations

import traceback
from datetime import date, datetime, timedelta

import pandas as pd

from .clients import EasyClient, OlosClient
from .db import engine
from .logging_setup import get_logger

log = get_logger("etl")


class ETLService:
    @staticmethod
    def _salvar(df: pd.DataFrame, tabela: str, schema_min: set | None = None) -> int:
        if df is None or df.empty:
            log.warning(f"DataFrame vazio — {tabela} não atualizada")
            return 0
        if schema_min:
            faltando = schema_min - set(df.columns)
            if faltando:
                log.error(f"Schema inválido para '{tabela}': {faltando}")
                return 0
        df = df.copy()
        df["etl_ts"] = datetime.utcnow()
        try:
            df.to_sql(tabela, engine, if_exists="append", index=False, method="multi", chunksize=500)
            log.info(f"{len(df)} linha(s) → {tabela}")
            return len(df)
        except Exception as e:
            log.error(f"Erro ao salvar '{tabela}': {e}")
            return 0

    @staticmethod
    def run_etl() -> dict:
        log.info("=== ETL Iniciado ===")
        inicio = datetime.utcnow()
        resultado = {}

        # Agentes
        try:
            df = pd.DataFrame(OlosClient.get_agents())
            if not df.empty and "status" in df.columns:
                df["status"] = df["status"].str.upper().str.strip()
            resultado["agentes"] = ETLService._salvar(df, "agents", {"agente_id", "nome", "status"})
        except Exception:
            log.error(f"Falha agentes:\n{traceback.format_exc()}")
            resultado["agentes"] = 0

        # Chamadas
        try:
            ontem = (date.today() - timedelta(days=1)).isoformat()
            df = pd.DataFrame(OlosClient.get_calls(data_inicio=ontem))
            if not df.empty and "telefone" in df.columns:
                df["ddd"] = df["telefone"].astype(str).str.replace(r"\D", "", regex=True).str[:2]
            resultado["chamadas"] = ETLService._salvar(df, "calls", {"call_id", "status"})
        except Exception:
            log.error(f"Falha chamadas:\n{traceback.format_exc()}")
            resultado["chamadas"] = 0

        # Snapshot de campanhas
        try:
            df = pd.DataFrame(OlosClient.get_campaign_snapshot())
            resultado["campanhas"] = ETLService._salvar(df, "campaign_snapshot")
        except Exception:
            log.error(f"Falha snapshot:\n{traceback.format_exc()}")
            resultado["campanhas"] = 0

        # Status de mailing
        try:
            df = pd.DataFrame(OlosClient.get_mailing_status())
            resultado["mailing"] = ETLService._salvar(df, "mailing_status")
        except Exception:
            log.error(f"Falha mailing:\n{traceback.format_exc()}")
            resultado["mailing"] = 0

        # Clientes / carteira (EasyCollector)
        try:
            df = pd.DataFrame(EasyClient.get_customers())
            if not df.empty and "telefone" in df.columns:
                df["telefone_limpo"] = df["telefone"].astype(str).str.replace(r"\D", "", regex=True)
                df["ddd"] = df["telefone_limpo"].str[:2]
            resultado["clientes"] = ETLService._salvar(df, "customers", {"cpf", "telefone"})
        except Exception:
            log.error(f"Falha clientes:\n{traceback.format_exc()}")
            resultado["clientes"] = 0

        # Promessas de pagamento
        try:
            df = pd.DataFrame(EasyClient.get_promises(data=date.today().isoformat()))
            resultado["promessas"] = ETLService._salvar(df, "easy_promessas")
        except Exception:
            log.error(f"Falha promessas:\n{traceback.format_exc()}")
            resultado["promessas"] = 0

        dur = (datetime.utcnow() - inicio).total_seconds()
        log.info(f"=== ETL Concluído em {dur:.1f}s | {sum(resultado.values())} linhas ===")
        return resultado
