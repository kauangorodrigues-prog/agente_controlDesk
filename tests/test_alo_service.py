"""Testes do serviço de integração ALO (mapeamento + lote), offline.

Faz *mock* do :class:`OlosClient` e roda sem banco e sem rede.

    python -m tests.test_alo_service
    pytest tests/test_alo_service.py
"""
from __future__ import annotations

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from control_desk import alo_service  # noqa: E402
from control_desk.alo_service import AloService, mapear_ligacao  # noqa: E402


def test_mapear_ligacao_campos_variados():
    raw = {
        "id": "abc-123",
        "phone": "11999998888",
        "carrier": "Vivo",
        "duration": 42,
        "connect_time": 4.3,
        "silence_time": 2.8,
        "amd_result": "Humano",
        "sip_cause": "200 OK",
        "transferred": True,
        "turns": [
            {"speaker": "cliente", "text": "Alô", "start": 1.2},
            {"speaker": "agente", "text": "Boa tarde", "start": 2.0},
        ],
    }
    call_id, lig = mapear_ligacao(raw)
    assert call_id == "abc-123"
    assert lig.operadora == "Vivo"
    assert lig.numero_chamado == "11999998888"
    assert lig.duracao_total_seg == 42
    assert lig.tempo_ate_conexao_seg == 4.3
    assert lig.transferencia is True
    assert len(lig.turnos) == 2
    assert lig.turnos[0].texto == "Alô"
    assert lig.turnos[0].inicio_seg == 1.2


def test_processar_lote_com_mock():
    chamadas = [
        {"id": "c1", "carrier": "Claro", "amd_result": "Humano",
         "turns": [{"speaker": "cliente", "text": "Alô", "start": 1.0}]},
        {"id": "c2", "carrier": "Claro",
         "transcription": [{"speaker": "ura", "text": "Deixe sua mensagem após o sinal"}]},
        {"id": "c3", "carrier": "Tim", "silence_time": 9.0, "duration": 10},
    ]
    # mock do conector — sem rede
    from control_desk.clients import OlosClient
    _bak = OlosClient.get_calls_para_alo
    OlosClient.get_calls_para_alo = classmethod(lambda cls, desde=None, limite=200: chamadas)
    try:
        resumo = AloService.processar_lote(persistir=False, usar_ia=False)
    finally:
        OlosClient.get_calls_para_alo = _bak

    assert resumo["processadas"] == 3
    assert resumo["alo"] == 1          # apenas c1
    assert resumo["nao_alo"] == 2      # c2 (caixa postal) + c3 (mudo)
    assert resumo["por_classificacao"].get("ALO REAL") == 1
    assert resumo["por_classificacao"].get("CAIXA POSTAL") == 1


def test_persistencia_sqlite_roundtrip():
    # Força um SQLite temporário e valida gravação + estatísticas.
    import tempfile
    from control_desk import alo_store

    tmp = os.path.join(tempfile.mkdtemp(), "alo_test.db")
    alo_store._SQLITE_PATH = tmp
    alo_store._pronto = False
    assert alo_store.backend() == "sqlite"

    chamadas = [
        {"id": "t1", "carrier": "Claro", "amd_result": "Humano",
         "turns": [{"speaker": "cliente", "text": "Alô", "start": 1.0}]},
        {"id": "t2", "carrier": "Vivo",
         "transcription": [{"speaker": "ura", "text": "Deixe sua mensagem após o sinal"}]},
    ]
    resumo = AloService.processar_payload(chamadas, persistir=True, usar_ia=False)
    assert resumo["processadas"] == 2
    assert resumo["persistidas"] == 2

    hist = AloService.historico(limite=10)
    assert len(hist) == 2

    est = AloService.estatisticas(dias=1)
    assert est["disponivel"] is True
    assert est["backend"] == "sqlite"
    assert int(est["resumo"]["n"]) == 2


def test_persistir_sem_banco_nao_quebra():
    # engine costuma ser None neste ambiente — persistência deve degradar em silêncio.
    from control_desk.alo_analyzer import ANALISADOR, Ligacao, Turno
    lig = Ligacao(operadora="X", turnos=[Turno("cliente", "Alô", 1.0)])
    r = ANALISADOR.analisar(lig, usar_ia=False)
    ok = alo_service._persistir("call-x", lig, r)
    assert ok in (True, False)  # não levanta exceção


def _main() -> int:
    testes = [v for k, v in sorted(globals().items()) if k.startswith("test_")]
    falhas = 0
    for t in testes:
        try:
            t()
            print(f"  ok   {t.__name__}")
        except AssertionError as e:
            falhas += 1
            print(f"  FALHA {t.__name__}: {e}")
        except Exception as e:  # noqa: BLE001
            falhas += 1
            print(f"  ERRO  {t.__name__}: {type(e).__name__}: {e}")
    total = len(testes)
    print(f"\n{total - falhas}/{total} testes passaram.")
    return 1 if falhas else 0


if __name__ == "__main__":
    raise SystemExit(_main())
