from __future__ import annotations

from datetime import datetime, timedelta

import numpy as np
import pandas as pd

from .db import engine
from .logging_setup import get_logger

log = get_logger("forecast")


class ForecastService:
    @staticmethod
    def _serie() -> pd.DataFrame:
        try:
            df = pd.read_sql(
                "SELECT DATE_TRUNC('hour', iniciada_em) AS ds, COUNT(*) AS y "
                "FROM calls WHERE iniciada_em >= NOW() - INTERVAL '180 days' "
                "GROUP BY 1 ORDER BY 1",
                engine,
            )
            df["ds"] = pd.to_datetime(df["ds"])
            return df
        except Exception as e:
            log.error(f"Falha ao carregar série histórica: {e}")
            return pd.DataFrame()

    @staticmethod
    def _fallback(df: pd.DataFrame, periodos: int) -> pd.DataFrame:
        df = df.copy()
        df["dow"] = df["ds"].dt.dayofweek
        df["hora"] = df["ds"].dt.hour
        medias = df.groupby(["dow", "hora"])["y"].mean()
        ultima = df["ds"].max()
        rows = []
        for i in range(1, periodos + 1):
            prox = ultima + timedelta(hours=i)
            m = medias.get((prox.dayofweek, prox.hour), df["y"].mean())
            rows.append({
                "ds": prox,
                "yhat": round(max(m, 0)),
                "yhat_lower": round(max(m * 0.80, 0)),
                "yhat_upper": round(m * 1.20),
            })
        return pd.DataFrame(rows)

    @staticmethod
    def generate_forecast(periodos: int = 24, tma_min: float = 5.0) -> pd.DataFrame:
        log.info("Gerando previsão de volume...")
        df = ForecastService._serie()
        if df.empty or len(df) < 48:
            log.warning("Histórico insuficiente para forecast.")
            return pd.DataFrame()

        try:
            from prophet import Prophet
            m = Prophet(weekly_seasonality=True, daily_seasonality=True, yearly_seasonality=False)
            m.fit(df[["ds", "y"]])
            futuro = m.make_future_dataframe(periods=periodos, freq="h")  # pandas 2.x+ usa 'h' minúsculo
            fc = m.predict(futuro)
            fc = fc[["ds", "yhat", "yhat_lower", "yhat_upper"]].tail(periodos)
            log.info("Método: Prophet")
        except ImportError:
            log.warning("Prophet não instalado — usando fallback de média móvel.")
            fc = ForecastService._fallback(df, periodos)
        except Exception as e:
            log.warning(f"Prophet falhou ({e}) — usando fallback de média móvel.")
            fc = ForecastService._fallback(df, periodos)

        fc["agentes_necessarios"] = (fc["yhat"] * (tma_min / 60)).apply(np.ceil).clip(lower=0).astype(int)
        fc["gerado_em"] = datetime.utcnow()

        try:
            fc.to_sql("forecast_calls", engine, if_exists="append", index=False)
        except Exception as e:
            log.error(f"Erro ao salvar forecast: {e}")

        return fc
