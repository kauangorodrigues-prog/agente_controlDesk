"""Testes da camada de resiliência (Fase 2): retry, circuit breaker,
timeout e Dead Letter Queue. Não dependem de banco."""
import importlib
import time

import pytest

mod = importlib.import_module("agente_ia_control_desk")


# ── retry_call ──────────────────────────────────────────────
def test_retry_sucesso_apos_falhas(monkeypatch):
    monkeypatch.setattr(mod.time, "sleep", lambda *_: None)  # não esperar
    tentativas = {"n": 0}

    def flaky():
        tentativas["n"] += 1
        if tentativas["n"] < 3:
            raise ValueError("ainda não")
        return "ok"

    assert mod.retry_call(flaky, max_retries=5, nome="t") == "ok"
    assert tentativas["n"] == 3


def test_retry_estoura_e_propaga(monkeypatch):
    monkeypatch.setattr(mod.time, "sleep", lambda *_: None)
    chamadas = {"n": 0}

    def sempre_falha():
        chamadas["n"] += 1
        raise RuntimeError("boom")

    with pytest.raises(RuntimeError):
        mod.retry_call(sempre_falha, max_retries=2, nome="t")
    assert chamadas["n"] == 3  # 1 original + 2 retries


# ── CircuitBreaker ──────────────────────────────────────────
def test_circuit_breaker_abre_e_meio_abre(monkeypatch):
    cb = mod.CircuitBreaker(fail_threshold=2, reset_timeout=10, nome="cb")
    assert cb.permitir() is True

    def falha():
        raise ValueError("x")

    for _ in range(2):
        with pytest.raises(ValueError):
            cb.chamar(falha)
    assert cb.estado == "OPEN"
    assert cb.permitir() is False  # barra chamadas

    # avança o relógio além do reset → HALF_OPEN permite uma tentativa
    monkeypatch.setattr(mod.time, "time", lambda: cb.aberto_em + 11)
    assert cb.permitir() is True
    assert cb.estado == "HALF_OPEN"

    # sucesso em half-open fecha o circuito
    assert cb.chamar(lambda: "ok") == "ok"
    assert cb.estado == "CLOSED"


def test_circuit_breaker_bloqueia_com_excecao_propria():
    cb = mod.CircuitBreaker(fail_threshold=1, reset_timeout=999, nome="cb")
    with pytest.raises(ValueError):
        cb.chamar(lambda: (_ for _ in ()).throw(ValueError()))
    with pytest.raises(mod.CircuitBreakerOpen):
        cb.chamar(lambda: "nunca chega")


# ── executar_com_timeout ────────────────────────────────────
def test_timeout_dispara():
    with pytest.raises(TimeoutError):
        mod.executar_com_timeout(lambda: time.sleep(1.0), timeout_s=0.15, nome="lento")


def test_timeout_retorna_valor_rapido():
    assert mod.executar_com_timeout(lambda: 42, timeout_s=5, nome="rapido") == 42


def test_timeout_zero_executa_direto():
    assert mod.executar_com_timeout(lambda: "direto", timeout_s=0, nome="x") == "direto"


# ── Dead Letter Queue ───────────────────────────────────────
def test_dlq_registrar_persiste_e_alerta(monkeypatch):
    capturado = {}
    monkeypatch.setattr(mod, "executar_comando",
                        lambda sql, params=None: capturado.update(params or {}))
    alertas = {"n": 0}
    monkeypatch.setattr(mod, "send_webhook_alert", lambda *a, **k: alertas.update(n=alertas["n"] + 1))
    mod.DeadLetterQueue.registrar("job_x", "erro grave", tentativas=3)
    assert capturado.get("o") == "job_x"
    assert capturado.get("t") == 3
    assert alertas["n"] == 1


# ── _safe_run roteia falha terminal para a DLQ ──────────────
def test_safe_run_falha_vai_para_dlq(monkeypatch):
    monkeypatch.setattr(mod, "JOB_STATS", {})
    registros = []
    monkeypatch.setattr(mod.DeadLetterQueue, "registrar",
                        staticmethod(lambda *a, **k: registros.append((a, k))))
    mod._safe_run(lambda: (_ for _ in ()).throw(RuntimeError("falhou")), "job_dlq")
    assert mod.JOB_STATS["job_dlq"]["last_status"] == "erro"
    assert len(registros) == 1  # foi para a DLQ
