"""Cache com backend Redis (opcional) e fallback em memória (camada core).

Evita consultas repetidas (KPIs, configs, feriados, forecast). Usa Redis se
REDIS_URL estiver definido e a lib disponível; caso contrário, cai para um
cache TTL em processo — a app funciona igual, sem infra externa.

Depende apenas de `app.config` (CFG) e do logger — sem conhecer camadas acima.
"""
from __future__ import annotations

import json
import logging
import threading
import time

from app.config import CFG

log = logging.getLogger("ControlDesk")


class MemoryCache:
    """Cache TTL em memória, thread-safe. Backend padrão (sem dependências)."""

    def __init__(self):
        self._dados: dict = {}
        self._lock = threading.Lock()

    def get(self, chave: str):
        with self._lock:
            item = self._dados.get(chave)
            if not item:
                return None
            valor, expira = item
            if expira and time.time() > expira:
                self._dados.pop(chave, None)
                return None
            return valor

    def set(self, chave: str, valor, ttl: int = None):
        expira = (time.time() + ttl) if ttl else None
        with self._lock:
            self._dados[chave] = (valor, expira)

    def delete(self, chave: str):
        with self._lock:
            self._dados.pop(chave, None)

    def clear(self):
        with self._lock:
            self._dados.clear()


class RedisCache:
    """Backend Redis (serialização JSON). Usado quando REDIS_URL está definido."""

    def __init__(self, client):
        self._r = client

    def get(self, chave: str):
        try:
            bruto = self._r.get(chave)
            return json.loads(bruto) if bruto is not None else None
        except Exception as e:
            log.debug(f"[Cache] get falhou ({chave}): {e}")
            return None

    def set(self, chave: str, valor, ttl: int = None):
        try:
            dado = json.dumps(valor, default=str)
            self._r.set(chave, dado, ex=ttl or None)
        except Exception as e:
            log.debug(f"[Cache] set falhou ({chave}): {e}")

    def delete(self, chave: str):
        try:
            self._r.delete(chave)
        except Exception:
            pass

    def clear(self):
        try:
            self._r.flushdb()
        except Exception:
            pass


def _build_cache():
    if CFG.REDIS_URL:
        try:
            import redis
            client = redis.Redis.from_url(CFG.REDIS_URL, socket_timeout=2, decode_responses=True)
            client.ping()
            log.info("[Cache] Backend: Redis")
            return RedisCache(client)
        except Exception as e:
            log.warning(f"[Cache] Redis indisponível ({e}); usando cache em memória.")
    return MemoryCache()


CACHE = _build_cache()


def cache_get_or_set(chave: str, ttl: int, produtor):
    """Retorna o valor cacheado ou executa `produtor()`, cacheia e retorna."""
    valor = CACHE.get(chave)
    if valor is not None:
        return valor
    valor = produtor()
    if valor is not None:
        CACHE.set(chave, valor, ttl)
    return valor
