"""Observabilidade: request-id, logging estruturado e métricas simples.

Fornece rastreabilidade de requisições (correlação por X-Request-ID) e um
coletor de métricas em memória exposto em /metrics — sem dependências externas.
"""
from __future__ import annotations

import logging
import time
import uuid
from collections import defaultdict
from contextvars import ContextVar

# ID de correlação disponível em todo o ciclo da requisição.
request_id_ctx: ContextVar[str] = ContextVar("request_id", default="-")


class RequestIdFilter(logging.Filter):
    """Injeta o request_id atual em cada registro de log."""

    def filter(self, record: logging.LogRecord) -> bool:
        record.request_id = request_id_ctx.get()
        return True


def new_request_id() -> str:
    return uuid.uuid4().hex[:16]


class Metrics:
    """Coletor de métricas leve em memória (contadores + latências)."""

    def __init__(self) -> None:
        self.requests_total: dict[str, int] = defaultdict(int)
        self.status_total: dict[int, int] = defaultdict(int)
        self.latency_sum_ms: float = 0.0
        self.latency_count: int = 0
        self._started = time.time()

    def observe(self, method: str, status_code: int, elapsed_ms: float) -> None:
        self.requests_total[method] += 1
        self.status_total[status_code] += 1
        self.latency_sum_ms += elapsed_ms
        self.latency_count += 1

    def snapshot(self) -> dict:
        avg = self.latency_sum_ms / self.latency_count if self.latency_count else 0.0
        return {
            "uptime_seconds": round(time.time() - self._started, 1),
            "requests_total": dict(self.requests_total),
            "requests_by_status": {str(k): v for k, v in self.status_total.items()},
            "avg_latency_ms": round(avg, 2),
            "total_requests": self.latency_count,
        }


metrics = Metrics()
