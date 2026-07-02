"""Testes da camada de observabilidade (Fase 1): logging estruturado,
registro de jobs e health checks. Não dependem de banco."""
import importlib
import json
import logging

import pytest

mod = importlib.import_module("agente_ia_control_desk")


# ── Correlation ID ──────────────────────────────────────────
def test_set_get_correlation_id():
    cid = mod.set_correlation_id("abc123")
    assert cid == "abc123"
    assert mod.get_correlation_id() == "abc123"


def test_set_correlation_id_gera_quando_vazio():
    cid = mod.set_correlation_id()
    assert cid and mod.get_correlation_id() == cid


# ── JSON formatter ──────────────────────────────────────────
def test_json_formatter_produz_json_valido():
    rec = logging.LogRecord("t", logging.INFO, __file__, 1, "oi mundo", None, None)
    rec.correlation_id = "cid-1"
    rec.job_id = "etl"
    out = mod.JsonFormatter().format(rec)
    data = json.loads(out)
    assert data["message"] == "oi mundo"
    assert data["level"] == "INFO"
    assert data["correlation_id"] == "cid-1"
    assert data["job_id"] == "etl"


# ── Registro de execução de jobs ────────────────────────────
def test_registrar_execucao_job_acumula(monkeypatch):
    # isola o registro global para não interferir noutros testes
    monkeypatch.setattr(mod, "JOB_STATS", {})
    mod.registrar_execucao_job("teste", "ok", 1.0)
    mod.registrar_execucao_job("teste", "erro", 3.0, erro="boom")
    st = mod.JOB_STATS["teste"]
    assert st["runs"] == 2
    assert st["failures"] == 1
    assert st["last_status"] == "erro"
    assert st["last_error"] == "boom"
    assert st["avg_duracao_s"] == 2.0
    assert st["success_rate"] == 0.5


def test_safe_run_registra_sucesso_e_erro(monkeypatch):
    monkeypatch.setattr(mod, "JOB_STATS", {})
    mod._safe_run(lambda: None, "job_ok")
    mod._safe_run(lambda: (_ for _ in ()).throw(ValueError("x")), "job_err")
    assert mod.JOB_STATS["job_ok"]["last_status"] == "ok"
    assert mod.JOB_STATS["job_err"]["last_status"] == "erro"
    assert mod.JOB_STATS["job_err"]["failures"] == 1


# ── Health helpers (sem banco/scheduler ativos) ─────────────
def test_health_jobs_shape():
    h = mod.health_jobs()
    assert set(h) >= {"scheduler_ativo", "agendados", "jobs"}
    assert isinstance(h["agendados"], list)


def test_recursos_sistema_tem_threads():
    r = mod._recursos_sistema()
    assert "threads" in r and r["threads"] >= 1


def test_ping_api_nao_configurado():
    d = mod._ping_api("", "")
    assert d["status"] == "nao_configurado"
    assert d["reachable"] is None
