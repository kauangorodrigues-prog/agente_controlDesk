"""Testes do ETL Enterprise (Melhoria 1): construção do UPSERT, dedup,
watermark e retenção. Não dependem de banco (usam mocks)."""
import importlib

import pandas as pd
import pytest

mod = importlib.import_module("agente_ia_control_desk")
Repo = mod.PostgresRepository


# ── Construção do SQL de UPSERT ─────────────────────────────
def test_build_upsert_sql_com_update():
    sql = Repo._build_upsert_sql("calls", ["call_id", "status", "etl_ts"], ["call_id"])
    assert "INSERT INTO calls (call_id, status, etl_ts)" in sql
    assert "ON CONFLICT (call_id)" in sql
    assert "status = EXCLUDED.status" in sql
    assert "call_id = EXCLUDED.call_id" not in sql  # a chave não é atualizada


def test_build_upsert_sql_apenas_chaves_faz_nothing():
    sql = Repo._build_upsert_sql("t", ["id"], ["id"])
    assert sql.strip().endswith("DO NOTHING")


def test_build_upsert_sql_rejeita_identificador_malicioso():
    with pytest.raises(ValueError):
        Repo._build_upsert_sql("calls; DROP TABLE calls", ["call_id"], ["call_id"])
    with pytest.raises(ValueError):
        Repo._build_upsert_sql("calls", ["a)-- ", "b"], ["a"])


# ── Conversão de linhas (NaN→None, numpy→python) ────────────
def test_linhas_converte_nan_e_numpy():
    df = pd.DataFrame({"a": [1, 2], "b": [None, "x"]})
    linhas = Repo._linhas(df)
    assert linhas[0]["b"] is None
    assert linhas[0]["a"] == 1 and not hasattr(linhas[0]["a"], "item")  # já é int python


def test_upsert_chave_ausente_erra():
    df = pd.DataFrame({"status": ["ok"]})
    with pytest.raises(ValueError):
        Repo.upsert("calls", df, ["call_id"])


# ── Watermark ───────────────────────────────────────────────
def test_watermark_get_default(monkeypatch):
    monkeypatch.setattr(mod, "executar_query", lambda *a, **k: [])
    assert mod.WatermarkRepository.get("calls", default="2020-01-01") == "2020-01-01"


def test_watermark_get_valor(monkeypatch):
    monkeypatch.setattr(mod, "executar_query", lambda *a, **k: [{"valor": "2026-01-01T00:00:00"}])
    assert mod.WatermarkRepository.get("calls") == "2026-01-01T00:00:00"


# ── _salvar: caminho idempotente e dedup ────────────────────
def test_salvar_usa_upsert_e_dedup(monkeypatch):
    capturas = {}

    def fake_upsert(tabela, df, chaves):
        capturas["tabela"] = tabela
        capturas["linhas"] = len(df)
        capturas["chaves"] = chaves
        return len(df)

    monkeypatch.setattr(mod.PostgresRepository, "upsert", staticmethod(fake_upsert))
    monkeypatch.setattr(mod.CFG, "ETL_UPSERT", True)
    # duas linhas com o mesmo call_id → dedup deve deixar 1
    df = pd.DataFrame({"call_id": ["A", "A", "B"], "status": ["x", "y", "z"]})
    n = mod.ETLService._salvar(df, "calls", {"call_id", "status"})
    assert capturas["tabela"] == "calls"
    assert capturas["chaves"] == ["call_id"]
    assert capturas["linhas"] == 2  # A (dedup) + B
    assert n == 2


def test_salvar_fallback_para_append_quando_upsert_falha(monkeypatch):
    def boom(*a, **k):
        raise RuntimeError("sem índice único")
    appended = {}
    monkeypatch.setattr(mod.PostgresRepository, "upsert", staticmethod(boom))
    monkeypatch.setattr(mod.CFG, "ETL_UPSERT", True)
    # intercepta o to_sql do DataFrame para simular o append sem banco
    monkeypatch.setattr(pd.DataFrame, "to_sql", lambda self, *a, **k: appended.update(n=len(self)))
    df = pd.DataFrame({"call_id": ["A"], "status": ["x"]})
    n = mod.ETLService._salvar(df, "calls", {"call_id", "status"})
    assert appended.get("n") == 1  # caiu para append
    assert n == 1


# ── Retenção desligada por padrão ───────────────────────────
def test_compactar_desligado_por_padrao(monkeypatch):
    monkeypatch.setattr(mod.CFG, "ETL_RETENCAO_DIAS", 0)
    assert mod.ETLService.compactar_snapshots()["status"] == "desabilitado"
