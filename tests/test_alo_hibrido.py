"""Testes do modo híbrido (heurística + IA só nas duvidosas), offline.

A IA é mockada — não há rede nem chave real.

    python -m tests.test_alo_hibrido
    pytest tests/test_alo_hibrido.py
"""
from __future__ import annotations

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from control_desk import alo_analyzer as A  # noqa: E402
from control_desk.alo_analyzer import (  # noqa: E402
    ALO_REAL, ANALISADOR, AnaliseResultado, Ligacao, OUTRO, Turno,
)


def _mock_ia(retorno_classe=ALO_REAL):
    """Substitui a IA por um resultado fixo e a marca como disponível."""
    def fake(lig):
        r = AnaliseResultado(origem="ia")
        r.classificacao = retorno_classe
        r.houve_alo = True
        r.grau_confianca = 99
        r.justificativa = "análise IA (mock)"
        return r
    A._ia_disponivel = lambda: True
    A._analisar_ia = fake


def _restaurar(orig_disp, orig_ia):
    A._ia_disponivel = orig_disp
    A._analisar_ia = orig_ia


def test_hibrido_alta_confianca_nao_chama_ia():
    orig_disp, orig_ia = A._ia_disponivel, A._analisar_ia
    _mock_ia()
    try:
        # ALO claro → heurística com confiança 95 (> limiar 80) → não escala.
        lig = Ligacao(operadora="Claro", amd="Humano",
                      turnos=[Turno("cliente", "Alô, quem fala?", 1.0)])
        r = ANALISADOR.analisar(lig, modo="hibrido")
        assert r.origem == "heuristica"
        assert r.escalado_para_ia is False
        assert r.classificacao == ALO_REAL
    finally:
        _restaurar(orig_disp, orig_ia)


def test_hibrido_baixa_confianca_escala_para_ia():
    orig_disp, orig_ia = A._ia_disponivel, A._analisar_ia
    _mock_ia(retorno_classe=ALO_REAL)
    try:
        # Sem sinais claros e sem AMD → heurística devolve OUTRO / confiança baixa → escala.
        lig = Ligacao(operadora="Claro")
        heur = A._analisar_heuristica(lig)
        assert heur.classificacao == OUTRO  # pré-condição: caso realmente duvidoso
        r = ANALISADOR.analisar(lig, modo="hibrido")
        assert r.origem == "ia"
        assert r.escalado_para_ia is True
    finally:
        _restaurar(orig_disp, orig_ia)


def test_modo_ia_sempre_usa_ia():
    orig_disp, orig_ia = A._ia_disponivel, A._analisar_ia
    _mock_ia()
    try:
        lig = Ligacao(operadora="Claro", amd="Humano",
                      turnos=[Turno("cliente", "Alô", 1.0)])
        r = ANALISADOR.analisar(lig, modo="ia")
        assert r.origem == "ia"
    finally:
        _restaurar(orig_disp, orig_ia)


def test_modo_heuristica_nunca_usa_ia():
    orig_disp, orig_ia = A._ia_disponivel, A._analisar_ia
    _mock_ia()
    try:
        lig = Ligacao(operadora="Claro")  # caso duvidoso
        r = ANALISADOR.analisar(lig, modo="heuristica")
        assert r.origem == "heuristica"
        assert r.escalado_para_ia is False
    finally:
        _restaurar(orig_disp, orig_ia)


def test_hibrido_sem_ia_disponivel_degrada():
    orig_disp, orig_ia = A._ia_disponivel, A._analisar_ia
    A._ia_disponivel = lambda: False  # sem chave/pacote
    try:
        lig = Ligacao(operadora="Claro")  # duvidoso, mas IA indisponível
        r = ANALISADOR.analisar(lig, modo="hibrido")
        assert r.origem == "heuristica"
        assert r.escalado_para_ia is False
    finally:
        _restaurar(orig_disp, orig_ia)


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
