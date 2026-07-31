"""Testes da matriz de confusão / métricas de acurácia — offline, determinístico.

    python -m tests.test_alo_matriz
    pytest tests/test_alo_matriz.py
"""
from __future__ import annotations

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from control_desk import alo_matriz  # noqa: E402


def test_matriz_perfeita():
    pares = [("ALO REAL", "ALO REAL")] * 3 + [("MUDO", "MUDO")] * 2
    rel = alo_matriz.avaliar(pares)
    assert rel["acuracia"] == 1.0
    assert rel["por_classe"]["ALO REAL"]["precisao"] == 1.0
    assert rel["por_classe"]["MUDO"]["recall"] == 1.0


def test_precisao_recall_com_erros():
    # 8 ALO reais: 6 certos, 2 confundidos com CAIXA POSTAL.
    pares = [("ALO REAL", "ALO REAL")] * 6 + [("ALO REAL", "CAIXA POSTAL")] * 2
    pares += [("CAIXA POSTAL", "CAIXA POSTAL")] * 4
    rel = alo_matriz.avaliar(pares)
    assert rel["por_classe"]["ALO REAL"]["recall"] == 0.75          # 6/8
    # CAIXA POSTAL: 4 certos + 2 falsos positivos -> precisão 4/6
    assert abs(rel["por_classe"]["CAIXA POSTAL"]["precisao"] - 0.667) < 0.01
    assert rel["acuracia"] == round(10 / 12, 3)


def test_calibracao_e_operadora():
    itens = [
        {"classificacao_humana": "ALO REAL", "classificacao_robo": "ALO REAL",
         "operadora": "Claro", "decisao": "automatica"},
        {"classificacao_humana": "ALO REAL", "classificacao_robo": "ALO REAL",
         "operadora": "Claro", "decisao": "automatica"},
        {"classificacao_humana": "MUDO", "classificacao_robo": "OUTRO",
         "operadora": "Tim", "decisao": "auditoria_humana"},
    ]
    rel = alo_matriz.avaliar_itens(itens)
    assert rel["calibracao_faixas"]["automatica"]["acuracia"] == 1.0
    assert rel["calibracao_faixas"]["auditoria_humana"]["acuracia"] == 0.0
    assert rel["por_operadora"]["Claro"]["acuracia"] == 1.0


def test_roda_robo_quando_sem_predicao():
    # Sem classificacao_robo -> o robô é rodado sobre a linha (transcrição real).
    itens = [{
        "classificacao_humana": "CAIXA POSTAL",
        "transcricao": "Deixe sua mensagem após o sinal.",
        "operadora": "Vivo",
    }]
    rel = alo_matriz.avaliar_itens(itens, modo="heuristica")
    assert rel["total"] == 1
    assert rel["acuracia"] == 1.0  # robô classifica como CAIXA POSTAL, bate com o humano


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
