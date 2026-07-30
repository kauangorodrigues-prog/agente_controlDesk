"""Testes do pipeline de áudio e das faixas de decisão — offline (transcrição mockada).

    python -m tests.test_alo_transcricao
    pytest tests/test_alo_transcricao.py
"""
from __future__ import annotations

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from control_desk import alo_service  # noqa: E402
from control_desk import alo_transcricao as tr  # noqa: E402
from control_desk.alo_analyzer import ANALISADOR, Ligacao, Turno  # noqa: E402


def test_parse_nome_gravacao():
    nome = "1115829654_AuthLogin1722016105060_073999180792_454_7511_20260724_080025.mp3"
    m = tr.parse_nome_gravacao(nome)
    assert m["call_id"] == "1115829654"
    assert m["numero_chamado"] == "073999180792"
    assert m["ddd"] == "73"
    assert m["data"] == "20260724"
    assert m["hora"] == "080025"


def test_faixas_de_decisao():
    # confiança alta (ALO claro = 95) -> automatica
    r = ANALISADOR.analisar(
        Ligacao(operadora="Claro", amd="Humano", turnos=[Turno("cliente", "Alô", 1.0)]),
        modo="heuristica",
    )
    assert r.grau_confianca >= 90 and r.decisao == "automatica"

    # confiança baixa (sem sinais = 40) -> auditoria_humana
    r2 = ANALISADOR.analisar(Ligacao(operadora="Claro"), modo="heuristica")
    assert r2.grau_confianca < 70 and r2.decisao == "auditoria_humana"


def test_consolidacao_financeira():
    # MUDO é falha de operadora (glosa) -> exige consolidação humana
    lig = Ligacao(operadora="Tim", duracao_total_seg=10, tempo_silencio_seg=9.5)
    r = ANALISADOR.analisar(lig, modo="heuristica")
    assert r.classificacao == "MUDO"
    assert r.requer_consolidacao_humana is True


def test_analisar_audio_com_transcricao_mockada():
    # Mocka a transcrição e a duração — sem depender do faster-whisper nem de áudio real.
    _orig_disp, _orig_tr, _orig_dur = tr.disponivel, tr.transcrever, tr.duracao_mp3
    tr.disponivel = lambda: True
    tr.transcrever = lambda caminho, idioma=None: "Alô, quem fala?"
    tr.duracao_mp3 = lambda caminho: 12.0
    try:
        nome = "/tmp/1115829654_AuthLogin1_073999180792_454_7511_20260724_080025.mp3"
        out = alo_service.AloService.analisar_audio(nome, persistir=False, modo="heuristica")
        assert out["call_id"] == "1115829654"
        assert out["classificacao"] == "ALO REAL"
        assert out["transcricao"] == "Alô, quem fala?"
        assert out["duracao_seg"] == 12.0
        assert "decisao" in out
    finally:
        tr.disponivel, tr.transcrever, tr.duracao_mp3 = _orig_disp, _orig_tr, _orig_dur


def test_audio_mudo_vira_MUDO():
    # Gravação com áudio mas sem fala detectada (transcrição vazia) -> MUDO.
    _orig_tr, _orig_dur = tr.transcrever, tr.duracao_mp3
    tr.transcrever = lambda caminho, idioma=None: ""
    tr.duracao_mp3 = lambda caminho: 8.0
    try:
        out = alo_service.AloService.analisar_audio(
            "/tmp/999_x_11999999999_1_1_20260724_080000.mp3", persistir=False, modo="heuristica"
        )
        assert out["classificacao"] == "MUDO"
        assert out["houve_alo"] is False
    finally:
        tr.transcrever, tr.duracao_mp3 = _orig_tr, _orig_dur


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
