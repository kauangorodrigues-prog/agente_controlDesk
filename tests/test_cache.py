"""Testes do cache (Fase 3): backend em memória, TTL, get_or_set e
invalidação de feriados. Não dependem de Redis nem de banco."""
import importlib

import pytest

mod = importlib.import_module("agente_ia_control_desk")


def test_memory_cache_set_get():
    c = mod.MemoryCache()
    c.set("k", {"a": 1}, ttl=10)
    assert c.get("k") == {"a": 1}
    assert c.get("inexistente") is None


def test_memory_cache_ttl_expira(monkeypatch):
    c = mod.MemoryCache()
    t = [1000.0]
    monkeypatch.setattr(mod.time, "time", lambda: t[0])
    c.set("k", "v", ttl=5)
    assert c.get("k") == "v"
    t[0] += 6
    assert c.get("k") is None  # expirou


def test_memory_cache_delete_clear():
    c = mod.MemoryCache()
    c.set("k", "v", ttl=10)
    c.delete("k")
    assert c.get("k") is None
    c.set("a", 1, ttl=10)
    c.set("b", 2, ttl=10)
    c.clear()
    assert c.get("a") is None and c.get("b") is None


def test_cache_get_or_set_chama_produtor_uma_vez():
    mod.CACHE.clear()
    chamadas = {"n": 0}

    def produtor():
        chamadas["n"] += 1
        return {"x": 1}

    v1 = mod.cache_get_or_set("chave-teste", 60, produtor)
    v2 = mod.cache_get_or_set("chave-teste", 60, produtor)
    assert v1 == v2 == {"x": 1}
    assert chamadas["n"] == 1  # o segundo veio do cache


def test_cache_get_or_set_nao_cacheia_vazio():
    # Resultado vazio (falha transitória) NÃO deve ser cacheado.
    mod.CACHE.clear()
    chamadas = {"n": 0}

    def vazio():
        chamadas["n"] += 1
        return []

    mod.cache_get_or_set("k-vazio", 60, vazio)
    mod.cache_get_or_set("k-vazio", 60, vazio)
    assert chamadas["n"] == 2  # recomputou (não mascarou a falha)


def test_build_cache_memoria_sem_redis(monkeypatch):
    monkeypatch.setattr(mod.CFG, "REDIS_URL", "")
    assert isinstance(mod._build_cache(), mod.MemoryCache)


def test_feriados_invalidacao_bump_versao():
    mod.CACHE.clear()
    v0 = mod.HolidayService._cache_ver()
    mod.HolidayService._invalidar_cache()
    assert mod.HolidayService._cache_ver() == v0 + 1
