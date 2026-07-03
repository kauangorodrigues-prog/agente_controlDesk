"""Testes da heurística do analisador ALO / NÃO ALO.

Rodam 100% offline (``usar_ia=False``) — determinísticos, sem rede.

    python -m tests.test_alo_analyzer     # execução direta
    pytest tests/test_alo_analyzer.py     # se pytest estiver instalado
"""
from __future__ import annotations

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from control_desk.alo_analyzer import (  # noqa: E402
    ALO_REAL, ANALISADOR, CAIXA_POSTAL, DISCADOR, Ligacao, MUDO, OCUPADO,
    Turno, URA, _parse_transcricao,
)


def _analisar(lig: Ligacao):
    return ANALISADOR.analisar(lig, usar_ia=False)


def test_alo_real_por_saudacao():
    lig = Ligacao(
        amd="Humano",
        duracao_total_seg=45,
        turnos=[
            Turno("Cliente", "Alô", inicio_seg=1.2),
            Turno("Agente", "Boa tarde, falo com o senhor João?", inicio_seg=2.0),
        ],
    )
    r = _analisar(lig)
    assert r.houve_alo is True
    assert r.classificacao == ALO_REAL
    assert r.grau_confianca >= 90
    assert r.operadora_entregou == "SIM"


def test_caixa_postal():
    lig = Ligacao(
        amd="Maquina",
        transcricao='URA: "Você ligou para a caixa postal. Deixe sua mensagem após o sinal."',
    )
    r = _analisar(lig)
    assert r.houve_alo is False
    assert r.classificacao == CAIXA_POSTAL


def test_ura_menu():
    lig = Ligacao(
        transcricao='Sistema: "Para falar com um atendente, digite 1. Para financeiro, tecle 2."',
    )
    r = _analisar(lig)
    assert r.classificacao == URA
    assert r.houve_alo is False


def test_ligacao_muda():
    lig = Ligacao(duracao_total_seg=10, tempo_silencio_seg=9.5, transcricao="")
    r = _analisar(lig)
    assert r.classificacao == MUDO
    assert r.operadora_entregou == "NÃO"
    assert r.prob_falha_operadora >= 60
    assert "Silêncio excessivo" in r.indicios_falha


def test_erro_de_discagem():
    lig = Ligacao(
        transcricao='Sistema: "O número chamado não existe. Verifique o número discado."',
        causa_sip="unallocated number",
    )
    r = _analisar(lig)
    assert r.classificacao == DISCADOR
    assert r.prob_falha_discador >= 70


def test_ocupado_sip_486():
    lig = Ligacao(causa_sip="486 Busy Here", codigo_encerramento="busy")
    r = _analisar(lig)
    assert r.classificacao == OCUPADO
    assert r.houve_alo is False


def test_atraso_na_entrega():
    lig = Ligacao(
        amd="Humano",
        duracao_total_seg=30,
        turnos=[
            Turno("Cliente", "Alô", inicio_seg=1.0),
            Turno("Cliente", "Alguém? Tá me ouvindo?", inicio_seg=4.0),
            Turno("Agente", "Boa tarde", inicio_seg=7.0),
        ],
    )
    r = _analisar(lig)
    assert r.houve_alo is True
    assert r.houve_atraso is True
    assert r.tempo_atraso_seg >= 5.0
    assert r.atraso_prejudicou in {"Alto", "Crítico"}
    assert "Operador entrou atrasado" in r.indicios_falha
    assert r.score_final < 80


def test_falso_negativo_amd():
    # AMD marcou máquina, mas houve saudação humana.
    lig = Ligacao(
        amd="Maquina",
        turnos=[Turno("Cliente", "Oi, pois não?", inicio_seg=1.0)],
    )
    r = _analisar(lig)
    assert r.houve_alo is True
    assert r.falso_negativo_alo is True


def test_falso_positivo_amd():
    # AMD marcou humano, mas era caixa postal.
    lig = Ligacao(
        amd="Humano",
        transcricao='Sistema: "Deixe seu recado após o sinal."',
    )
    r = _analisar(lig)
    assert r.classificacao == CAIXA_POSTAL
    assert r.falso_positivo_alo is True


def test_parse_transcricao_livre():
    texto = 'Cliente:\n"Alô"\n\nAgente:\n"Boa tarde, tudo bem?"\n\nCliente:\n"Quem fala?"'
    turnos = _parse_transcricao(texto)
    assert len(turnos) == 3
    assert turnos[0].falante == "Cliente"
    assert turnos[0].texto == "Alô"
    assert turnos[1].falante == "Agente"


def test_analisar_dict_roundtrip():
    payload = {
        "operadora": "Vivo",
        "amd": "Humano",
        "turnos": [
            {"falante": "cliente", "texto": "Alô", "inicio_seg": 1.0},
            {"falante": "agente", "texto": "Boa noite", "inicio_seg": 1.8},
        ],
    }
    r = ANALISADOR.analisar_dict(dict(payload), usar_ia=False)
    assert r["classificacao"] == ALO_REAL
    assert r["houve_alo"] is True
    assert "metricas" in r
    assert 0 <= r["score_final"] <= 100


def test_metricas_calculadas():
    lig = Ligacao(
        amd="Humano",
        tempo_fala_seg=20,
        tempo_silencio_seg=5,
        tempo_espera_seg=2,
        tempo_ate_conexao_seg=3,
        turnos=[
            Turno("Cliente", "Alô", inicio_seg=2.0),
            Turno("Agente", "Boa tarde", inicio_seg=4.0),
        ],
    )
    r = _analisar(lig)
    assert r.metricas.tempo_ate_primeiro_alo_seg == 2.0
    assert r.metricas.tempo_ate_primeiro_operador_seg == 4.0
    assert r.metricas.tempo_util_seg == 20
    assert r.metricas.tempo_perdido_seg == 7.0


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
