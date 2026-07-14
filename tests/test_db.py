"""Testes da camada de banco (Fase 4): read replica fallback, paginação,
bulk insert, retry de leitura e coleta paralela do ETL. Sem banco real."""
import importlib

import pandas as pd
import pytest

mod = importlib.import_module("agente_ia_control_desk")


# ── Read replica: sem DATABASE_REPLICA_URL, engine_leitura == engine ──
def test_engine_leitura_cai_para_primaria_sem_replica():
    # No ambiente de teste não há DATABASE_REPLICA_URL configurada.
    assert mod.engine_leitura is mod.engine


# ── Paginação: monta LIMIT/OFFSET e detecta próxima página ──
def test_paginar_detecta_proxima(monkeypatch):
    capt = {}

    def fake_query(sql, params=None):
        capt["sql"] = sql
        capt["params"] = params
        # devolve por_pagina+1 linhas -> tem_proxima=True
        return [{"i": k} for k in range(params["_limit"])]

    monkeypatch.setattr(mod, "executar_query", fake_query)
    page = mod.PostgresRepository.paginar("SELECT * FROM t", pagina=2, por_pagina=10)
    assert "LIMIT :_limit OFFSET :_offset" in capt["sql"]
    assert capt["params"]["_limit"] == 11      # por_pagina + 1
    assert capt["params"]["_offset"] == 10     # (pagina-1)*por_pagina
    assert page["pagina"] == 2
    assert len(page["itens"]) == 10            # trunca ao tamanho da página
    assert page["tem_proxima"] is True


def test_paginar_ultima_pagina(monkeypatch):
    monkeypatch.setattr(mod, "executar_query", lambda sql, params=None: [{"i": 1}])
    page = mod.PostgresRepository.paginar("SELECT 1", pagina=1, por_pagina=10)
    assert page["tem_proxima"] is False
    assert len(page["itens"]) == 1


def test_paginar_limita_por_pagina(monkeypatch):
    capt = {}
    monkeypatch.setattr(mod, "executar_query",
                        lambda sql, params=None: capt.update(params or {}) or [])
    mod.PostgresRepository.paginar("SELECT 1", pagina=1, por_pagina=99999)
    assert capt["_limit"] <= 501  # teto de 500 (+1)


# ── bulk_insert monta INSERT e valida identificadores ──
def test_bulk_insert_vazio_retorna_zero():
    assert mod.PostgresRepository.bulk_insert("t", pd.DataFrame()) == 0


def test_bulk_insert_rejeita_tabela_maliciosa():
    df = pd.DataFrame({"a": [1]})
    with pytest.raises(ValueError):
        mod.PostgresRepository.bulk_insert("t; DROP TABLE t", df)


# ── ETL: coleta paralela devolve todas as fontes ──
def test_coletar_paralelo(monkeypatch):
    monkeypatch.setattr(mod.CFG, "ETL_PARALELO", True)
    tarefas = {
        "a": lambda: [1, 2],
        "b": lambda: [3],
        "c": lambda: (_ for _ in ()).throw(RuntimeError("x")),  # falha isolada
    }
    r = mod.ETLService._coletar(tarefas)
    assert r["a"] == [1, 2] and r["b"] == [3]
    assert r["c"] == []  # falha não derruba as outras fontes


def test_coletar_sequencial(monkeypatch):
    monkeypatch.setattr(mod.CFG, "ETL_PARALELO", False)
    r = mod.ETLService._coletar({"a": lambda: [1], "b": lambda: [2]})
    assert r == {"a": [1], "b": [2]}


# ── executar_query aplica retry em erro transiente ──
def test_executar_query_retry(monkeypatch):
    monkeypatch.setattr(mod.time, "sleep", lambda *_: None)
    monkeypatch.setattr(mod.CFG, "DB_READ_RETRY", 2)
    chamadas = {"n": 0}

    # força a exceção transiente conhecida
    transiente = mod._erros_transientes_db()[0]

    class FakeSession:
        def execute(self, *a, **k):
            chamadas["n"] += 1
            if chamadas["n"] < 2:
                err = transiente("SELECT 1", {}, Exception("conexão caiu"))
                err.connection_invalidated = True  # simula desconexão real
                raise err
            class R:
                def keys(self_): return ["x"]
                def fetchall(self_): return [(1,)]
            return R()
        def commit(self): pass
        def rollback(self): pass
        def close(self): pass

    import contextlib

    @contextlib.contextmanager
    def fake_get_db(leitura=False):
        yield FakeSession()

    # executar_query vive em app.core.database (Fase 6) e chama o get_db de lá.
    import app.core.database as _db
    monkeypatch.setattr(_db, "get_db", fake_get_db)
    linhas = mod.executar_query("SELECT 1")
    assert linhas == [{"x": 1}]
    assert chamadas["n"] == 2  # falhou 1x, sucesso na 2ª
