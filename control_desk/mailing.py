from __future__ import annotations

import os
import re
from datetime import date, datetime
from typing import Optional

import pandas as pd

from .config import CFG
from .db import engine
from .logging_setup import get_logger

log = get_logger("mailing")

DDDS_VALIDOS = {
    str(d) for d in
    list(range(11, 20)) + list(range(21, 30)) +
    list(range(31, 40)) + list(range(41, 50)) +
    list(range(51, 70)) + list(range(71, 100))
}

DDD_SCORE_MAP = {
    "11": 10, "21": 9, "31": 8, "41": 8, "51": 7,
    "71": 7, "61": 6, "85": 6, "81": 6,
}


class MailingScoreService:
    @staticmethod
    def validar_cpf(cpf: str) -> bool:
        cpf = re.sub(r"\D", "", str(cpf or ""))
        if len(cpf) != 11 or len(set(cpf)) == 1:
            return False
        for i in range(2):
            soma = sum(int(cpf[j]) * (10 + i - j) for j in range(9 + i))
            if (soma * 10 % 11) % 10 != int(cpf[9 + i]):
                return False
        return True

    @staticmethod
    def validar_telefone(tel: str) -> Optional[str]:
        digits = re.sub(r"\D", "", str(tel or ""))
        if len(digits) not in (10, 11):
            return None
        if digits[:2] not in DDDS_VALIDOS:
            return None
        return digits

    @staticmethod
    def calcular_score(row: pd.Series) -> float:
        if not {"cpf", "telefone"}.issubset(set(row.index)):
            return 0.0
        score = 0.0
        score += min(float(row.get("previous_cpc", 0) or 0) * 30, 30)
        dias = float(row.get("days_delay", 30) or 30)
        score += max(0.0, 20 - dias * 0.4)
        faixa = int(row.get("faixa_atraso_dias", 0) or 0)
        score += 15 if 30 <= faixa <= 90 else 8 if faixa < 30 else 4
        h = datetime.now().hour
        h_ini = int(row.get("melhor_hora_inicio", 8) or 8)
        h_fim = int(row.get("melhor_hora_fim", 20) or 20)
        if h_ini <= h <= h_fim:
            score += 15
        score += DDD_SCORE_MAP.get(str(row.get("ddd", ""))[:2], 5)
        if row.get("promessa_quebrada"):
            score -= 10
        return round(max(0.0, min(score, 100.0)), 2)

    @staticmethod
    def calculate_score(caminho_csv: Optional[str] = None) -> pd.DataFrame:
        if caminho_csv and os.path.exists(caminho_csv):
            df = pd.read_csv(caminho_csv, dtype=str)
        else:
            try:
                df = pd.read_sql("SELECT * FROM customers WHERE ativo = TRUE", engine)
            except Exception as e:
                log.error(f"Falha ao ler clientes do banco: {e}")
                return pd.DataFrame()

        if df.empty:
            return df

        if not {"cpf", "telefone"}.issubset(set(df.columns)):
            log.error("Colunas cpf/telefone ausentes.")
            return pd.DataFrame()

        df = df[df["cpf"].apply(MailingScoreService.validar_cpf)].copy()
        df["telefone_limpo"] = df["telefone"].apply(MailingScoreService.validar_telefone)
        df = df[df["telefone_limpo"].notna()].copy()
        df["ddd"] = df["telefone_limpo"].str[:2]

        if "captured_at" in df.columns:
            df = df.sort_values("captured_at", ascending=False)
        df = df.drop_duplicates(subset=["cpf"]).copy()

        for col in ["days_delay", "previous_cpc", "phone_score", "faixa_atraso_dias",
                    "melhor_hora_inicio", "melhor_hora_fim"]:
            if col in df.columns:
                df[col] = pd.to_numeric(df[col], errors="coerce").fillna(0)

        if "promessa_quebrada" in df.columns:
            df["promessa_quebrada"] = df["promessa_quebrada"].astype(str).isin(
                ["1", "True", "true", "t", "yes"]
            )

        df["score_discagem"] = df.apply(MailingScoreService.calcular_score, axis=1)
        df = df.sort_values("score_discagem", ascending=False).reset_index(drop=True)

        try:
            df["scored_at"] = datetime.utcnow()
            df.to_sql("mailing_scored", engine, if_exists="replace", index=False)
        except Exception as e:
            log.error(f"Erro ao salvar mailing_scored: {e}")

        os.makedirs(CFG.DIR_MAILING, exist_ok=True)
        saida = os.path.join(CFG.DIR_MAILING, f"mailing_priorizado_{date.today()}.csv")
        df.to_csv(saida, index=False)
        log.info(f"{len(df)} registros → {saida}")
        return df
