"""Rate limiting simples em memória para proteção contra brute-force.

Suficiente para uma única instância. Em produção com múltiplas réplicas,
troque por um backend compartilhado (Redis) mantendo a mesma interface.
"""
from __future__ import annotations

import threading
import time
from collections import defaultdict

_lock = threading.Lock()
_attempts: dict[str, list[float]] = defaultdict(list)


def is_locked(key: str, max_attempts: int, window_seconds: int) -> bool:
    """True se o número de falhas recentes atingiu o limite na janela."""
    now = time.time()
    with _lock:
        recent = [t for t in _attempts[key] if now - t < window_seconds]
        _attempts[key] = recent
        return len(recent) >= max_attempts


def record_failure(key: str) -> None:
    with _lock:
        _attempts[key].append(time.time())


def reset(key: str) -> None:
    with _lock:
        _attempts.pop(key, None)
