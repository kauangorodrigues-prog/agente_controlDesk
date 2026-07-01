from __future__ import annotations

import os

import joblib
import pandas as pd
from sklearn.ensemble import GradientBoostingClassifier
from sklearn.model_selection import train_test_split
from sklearn.preprocessing import LabelEncoder

from .config import CFG
from .db import engine
from .logging_setup import get_logger

log = get_logger("discagem")


class InteligenciaDiscagem:
    """
    Prevê a melhor janela de discagem (DDD/hora/dia da semana) para maximizar CPC,
    usando GradientBoosting. Modelo persistido em disco via joblib entre execuções.
    """

    def __init__(self) -> None:
        self.modelo: GradientBoostingClassifier | None = None
        self.le_ddd = LabelEncoder()
        os.makedirs(CFG.DIR_MODELOS, exist_ok=True)
        self._pkl = os.path.join(CFG.DIR_MODELOS, "modelo_cpc.pkl")
        self._carregar_disco()

    def _carregar_disco(self) -> None:
        if not os.path.exists(self._pkl):
            return
        try:
            payload = joblib.load(self._pkl)
            self.modelo = payload["modelo"]
            self.le_ddd = payload["le_ddd"]
            log.info(f"Modelo carregado do disco: {self._pkl}")
        except Exception as e:
            log.warning(f"Não foi possível carregar modelo do disco: {e}")

    def _salvar_disco(self) -> None:
        if self.modelo is None:
            return
        try:
            joblib.dump({"modelo": self.modelo, "le_ddd": self.le_ddd}, self._pkl)
            log.info(f"Modelo salvo em disco: {self._pkl}")
        except Exception as e:
            log.error(f"Falha ao salvar modelo: {e}")

    def carregar_historico(self, dias: int = 90) -> pd.DataFrame:
        sql = f"""
            SELECT
                SUBSTRING(telefone, 1, 2)::int      AS ddd,
                EXTRACT(HOUR FROM iniciada_em)::int AS hora,
                EXTRACT(DOW  FROM iniciada_em)::int AS dia_semana,
                CASE WHEN tipo_resultado IN ('CPC', 'RPC') THEN 1 ELSE 0 END AS cpc
            FROM calls
            WHERE iniciada_em >= NOW() - INTERVAL '{dias} days'
              AND telefone IS NOT NULL
        """
        try:
            df = pd.read_sql(sql, engine)
            log.info(f"Histórico: {len(df)} ligações / {dias} dias")
            return df
        except Exception as e:
            log.error(f"Falha ao carregar histórico: {e}")
            return pd.DataFrame()

    def treinar_modelo(self, df: pd.DataFrame) -> None:
        if df.empty or len(df) < 500:
            log.warning(f"Histórico insuficiente ({len(df)} registros; mínimo 500).")
            return
        feats = ["ddd", "hora", "dia_semana"]
        df = df.dropna(subset=feats + ["cpc"])
        X = df[feats].copy()
        X["ddd"] = self.le_ddd.fit_transform(X["ddd"].astype(str))
        y = df["cpc"]
        Xtr, Xte, ytr, yte = train_test_split(X, y, test_size=0.2, random_state=42)
        self.modelo = GradientBoostingClassifier(n_estimators=150, max_depth=4, random_state=42)
        self.modelo.fit(Xtr, ytr)
        acc = self.modelo.score(Xte, yte)
        log.info(f"Modelo treinado | Acurácia: {acc:.3f}")
        self._salvar_disco()

    def melhor_janela(self, ddd: str, top_n: int = 3) -> list[dict]:
        if self.modelo is None:
            return []
        cands = pd.DataFrame([
            {"ddd": 0, "hora": h, "dia_semana": d}
            for h in range(7, 21) for d in range(1, 6)
        ])
        try:
            cands["ddd"] = self.le_ddd.transform([ddd] * len(cands))
        except ValueError:
            cands["ddd"] = 0
        cands["prob_cpc"] = self.modelo.predict_proba(cands[["ddd", "hora", "dia_semana"]])[:, 1]
        dias_map = {1: "Seg", 2: "Ter", 3: "Qua", 4: "Qui", 5: "Sex"}
        return (
            cands.nlargest(top_n, "prob_cpc")[["hora", "dia_semana", "prob_cpc"]]
            .assign(dia_semana=lambda x: x["dia_semana"].map(dias_map))
            .to_dict("records")
        )


DISCAGEM = InteligenciaDiscagem()


def treinar_async() -> None:
    """Carrega histórico e treina o modelo (chamado em thread separada pelo scheduler)."""
    df = DISCAGEM.carregar_historico(dias=90)
    DISCAGEM.treinar_modelo(df)
