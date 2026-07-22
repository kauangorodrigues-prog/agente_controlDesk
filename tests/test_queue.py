"""Testes da fila de jobs (Fase 3): prioridades, registro, execução sync
e enfileiramento in-process. Não dependem de Celery/broker."""
import importlib
import threading

import pytest

mod = importlib.import_module("agente_ia_control_desk")


def test_prioridade_mapa_ordena():
    assert mod.Prioridade.MAPA["CRITICAL"] < mod.Prioridade.MAPA["HIGH"]
    assert mod.Prioridade.MAPA["HIGH"] < mod.Prioridade.MAPA["LOW"]
    assert set(mod.Prioridade.MAPA) == {"CRITICAL", "HIGH", "NORMAL", "LOW"}


def test_jobs_disponiveis():
    js = mod.JobQueue.jobs_disponiveis()
    assert "etl" in js and "forecast" in js and "pacing" in js


def test_executar_sync_desconhecido_erra():
    with pytest.raises(KeyError):
        mod.JobQueue.executar_sync("nao_existe")


def test_executar_sync_roda(monkeypatch):
    chamou = {"n": 0}
    monkeypatch.setitem(mod.JOBS_REGISTRO, "dummy_sync",
                        lambda: chamou.__setitem__("n", chamou["n"] + 1))
    r = mod.JobQueue.executar_sync("dummy_sync")
    assert r["modo"] == "sync"
    assert chamou["n"] == 1


def test_enfileirar_desconhecido_erra():
    with pytest.raises(KeyError):
        mod.JobQueue.enfileirar("nao_existe")


def test_enfileirar_in_process_executa(monkeypatch):
    monkeypatch.setattr(mod.CFG, "CELERY_BROKER_URL", "")  # força fila in-process
    ev = threading.Event()
    monkeypatch.setitem(mod.JOBS_REGISTRO, "dummy_fila", lambda: ev.set())
    r = mod.JobQueue.enfileirar("dummy_fila", "HIGH")
    assert r["modo"] == "fila"
    assert r["prioridade"] == "HIGH"
    assert ev.wait(timeout=5), "o job enfileirado não executou"


def test_status_fila_shape():
    s = mod.JobQueue.status()
    assert set(s) >= {"backend", "tamanho_fila", "workers", "jobs_disponiveis"}
