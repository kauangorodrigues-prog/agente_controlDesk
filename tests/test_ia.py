"""Testes da camada de IA (Fase 5): features, degradação para heurístico,
motor de decisão e ensemble de forecast. Treino real só se sklearn existir."""
import importlib

import numpy as np
import pandas as pd
import pytest

mod = importlib.import_module("agente_ia_control_desk")
PM = mod.PropensityModel


# ── Features ────────────────────────────────────────────────
def test_features_shape_e_colunas():
    df = pd.DataFrame({
        "previous_cpc": [0.5, None], "days_delay": [10, 40],
        "faixa_atraso_dias": [45, 5], "phone_score": [7, None],
        "ddd": ["11", "99"], "promessa_quebrada": ["true", "0"],
    })
    X = PM._features(df)
    assert list(X.columns) == PM.FEATURES
    assert len(X) == 2
    assert X.isnull().sum().sum() == 0            # NaN tratados
    assert X["promessa_quebrada"].tolist() == [1, 0]


def test_features_colunas_ausentes_usam_default():
    X = PM._features(pd.DataFrame({"cpf": ["1"]}))
    assert list(X.columns) == PM.FEATURES
    assert X["days_delay"].iloc[0] == 30          # default


# ── Degradação: sem modelo ativo, prever() retorna None ─────
def test_prever_sem_modelo_retorna_none(monkeypatch):
    monkeypatch.setattr(PM, "_cache_modelo", None)
    monkeypatch.setattr(PM, "_modelo_ativo", staticmethod(lambda: None))
    assert PM.prever(pd.DataFrame({"cpf": ["1"], "ddd": ["11"]})) is None


def test_status_sem_modelo(monkeypatch):
    monkeypatch.setattr(PM, "_modelo_ativo", staticmethod(lambda: None))
    s = PM.status()
    assert s["scorer"] == "heuristico"
    assert s["versao_ativa"] is None


# ── Decision engine (lógica pura sobre snapshots) ───────────
def test_decision_engine_recomenda_por_kpi():
    campanhas = [
        {"campanha_id": "A", "abandono_pct": 20.0, "ociosidade_pct": 2, "mailing_restante_pct": 50},
        {"campanha_id": "B", "abandono_pct": 1.0, "ociosidade_pct": 30, "mailing_restante_pct": 50},
        {"campanha_id": "C", "abandono_pct": 1.0, "ociosidade_pct": 2, "mailing_restante_pct": 2},
    ]
    recs = mod.DecisionEngine._analisar(campanhas)
    acoes = {r["campanha_id"]: r["acao"] for r in recs}
    assert acoes["A"] == "desacelerar_pacing"     # abandono alto
    assert acoes["B"] == "acelerar_pacing"        # ociosidade alta
    assert acoes["C"] == "repor_mailing"          # mailing crítico
    # ordenado por severidade desc
    assert recs[0]["severidade"] >= recs[-1]["severidade"]


def test_decision_engine_sem_problemas():
    campanhas = [{"campanha_id": "OK", "abandono_pct": 1, "ociosidade_pct": 2, "mailing_restante_pct": 80}]
    assert mod.DecisionEngine._analisar(campanhas) == []


# ── Forecast: EWMA e ensemble (sem banco) ───────────────────
def _serie_horaria(n=24 * 14):
    idx = pd.date_range("2026-01-01", periods=n, freq="h")
    y = 50 + 20 * np.sin(np.arange(n) * 2 * np.pi / 24) + np.random.default_rng(0).normal(0, 3, n)
    return pd.DataFrame({"ds": idx, "y": np.clip(y, 0, None)})


def test_ewma_gera_periodos():
    fc = mod.ForecastService._ewma(_serie_horaria(), 24)
    assert len(fc) == 24
    assert (fc["yhat"] >= 0).all()


def test_ensemble_colunas_e_positivo():
    fc = mod.ForecastService._ensemble(_serie_horaria(), 12)
    assert list(fc.columns) == ["ds", "yhat", "yhat_lower", "yhat_upper", "metodo"]
    assert len(fc) == 12
    assert (fc["yhat"] >= 0).all()
    assert (fc["yhat_lower"] <= fc["yhat_upper"]).all()
    assert fc["metodo"].iloc[0].startswith("ensemble(")


# ── Treino real (só se sklearn instalado) ───────────────────
def test_treinar_com_dados_sinteticos():
    pytest.importorskip("sklearn")
    rng = np.random.default_rng(1)
    n = 400
    # sinal: previous_cpc alto e days_delay baixo -> mais propenso a pagar
    prev = rng.random(n)
    dias = rng.integers(0, 120, n)
    prob = 1 / (1 + np.exp(-(3 * prev - 0.03 * dias)))
    y = (rng.random(n) < prob).astype(int)
    df = pd.DataFrame({
        "previous_cpc": prev, "days_delay": dias,
        "faixa_atraso_dias": dias, "phone_score": rng.random(n) * 10,
        "ddd": rng.choice(["11", "21", "31"], n), "promessa_quebrada": rng.integers(0, 2, n),
    })
    # treina sem tocar no banco (registro é monkeypatchado)
    saved = {}
    import agente_ia_control_desk as M
    orig_reg = M.PropensityModel._registrar_versao
    M.PropensityModel._registrar_versao = staticmethod(lambda *a, **k: saved.update(reg=True))
    try:
        r = M.PropensityModel.treinar(df=df, y=y)
    finally:
        M.PropensityModel._registrar_versao = orig_reg
    assert r["status"] == "treinado"
    assert r["n_treino"] > 0 and r["n_teste"] > 0
    assert r["auc"] is None or 0.0 <= r["auc"] <= 1.0
