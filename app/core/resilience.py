"""Resiliência: timeout, retry com backoff exponencial e circuit breaker.

Camada `core`: depende apenas da stdlib e do logger; não conhece as camadas
superiores (serviços/API).
"""
from __future__ import annotations

import concurrent.futures
import contextvars
import logging
import threading
import time

log = logging.getLogger("ControlDesk")


class CircuitBreakerOpen(Exception):
    """Sinaliza que o circuit breaker está aberto e a chamada foi barrada."""


# Executor dedicado para impor timeout em funções síncronas.
_JOB_TIMEOUT_EXECUTOR = concurrent.futures.ThreadPoolExecutor(
    max_workers=8, thread_name_prefix="jobtimeout"
)


def executar_com_timeout(fn, timeout_s: float, nome: str = ""):
    """Executa fn com timeout. Propaga o contexto (correlation id) para a thread.

    Limitação honesta: Python não permite matar uma thread à força — em caso de
    timeout, paramos de esperar e sinalizamos, mas a thread pode seguir até o fim.
    """
    if not timeout_s or timeout_s <= 0:
        return fn()
    ctx = contextvars.copy_context()
    fut = _JOB_TIMEOUT_EXECUTOR.submit(ctx.run, fn)
    try:
        return fut.result(timeout=timeout_s)
    except concurrent.futures.TimeoutError:
        raise TimeoutError(f"'{nome}' excedeu o timeout de {timeout_s}s")


def retry_call(fn, max_retries: int = 3, base_delay: float = 1.0,
               max_delay: float = 30.0, exceptions: tuple = (Exception,),
               nome: str = "", on_retry=None, retriavel=None):
    """Executa fn com retry de backoff exponencial. Reutilizável por jobs e I/O.

    `retriavel(e)` opcional: se fornecido e retornar False, a exceção é
    propagada sem retry (ex.: não reexecutar um statement_timeout)."""
    tentativa = 0
    while True:
        try:
            return fn()
        except exceptions as e:
            if retriavel is not None and not retriavel(e):
                raise
            tentativa += 1
            if tentativa > max_retries:
                raise
            delay = min(base_delay * (2 ** (tentativa - 1)), max_delay)
            if on_retry:
                try:
                    on_retry(tentativa, e)
                except Exception:
                    pass
            log.warning(f"[Retry] '{nome}' tentativa {tentativa}/{max_retries} falhou: {e}. "
                        f"Aguardando {delay:.1f}s")
            time.sleep(delay)


class CircuitBreaker:
    """Circuit breaker CLOSED → OPEN → HALF_OPEN (thread-safe)."""

    def __init__(self, fail_threshold: int = 5, reset_timeout: int = 60, nome: str = "cb"):
        self.fail_threshold = fail_threshold
        self.reset_timeout = reset_timeout
        self.nome = nome
        self.estado = "CLOSED"
        self.falhas = 0
        self.aberto_em = None
        self._lock = threading.Lock()

    def permitir(self) -> bool:
        with self._lock:
            if self.estado == "OPEN":
                if self.aberto_em and (time.time() - self.aberto_em) >= self.reset_timeout:
                    self.estado = "HALF_OPEN"
                    return True
                return False
            return True

    def registrar_sucesso(self):
        with self._lock:
            self.falhas = 0
            self.estado = "CLOSED"
            self.aberto_em = None

    def registrar_falha(self):
        with self._lock:
            self.falhas += 1
            if self.estado == "HALF_OPEN" or self.falhas >= self.fail_threshold:
                self.estado = "OPEN"
                self.aberto_em = time.time()

    def chamar(self, fn):
        if not self.permitir():
            raise CircuitBreakerOpen(f"Circuit breaker '{self.nome}' aberto")
        try:
            resultado = fn()
        except Exception:
            self.registrar_falha()
            raise
        self.registrar_sucesso()
        return resultado
