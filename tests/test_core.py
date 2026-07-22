"""Testes das funções puras (sem dependência de banco/API).

Rode com:  pytest -q
Requer apenas: pandas, numpy, requests (imports de topo do módulo) e pytest.
A criação da engine é tolerante a falhas, então o import funciona sem banco.
"""
from datetime import time as dtime

import pandas as pd

from agente_ia_control_desk import (
    MailingScoreService,
    PacingService,
    _str_para_time,
)


# ── Validação de CPF ────────────────────────────────────────
def test_validar_cpf_valido():
    assert MailingScoreService.validar_cpf("529.982.247-25") is True
    assert MailingScoreService.validar_cpf("52998224725") is True


def test_validar_cpf_invalido():
    assert MailingScoreService.validar_cpf("111.111.111-11") is False  # todos iguais
    assert MailingScoreService.validar_cpf("529.982.247-24") is False  # dígito errado
    assert MailingScoreService.validar_cpf("123") is False             # curto demais
    assert MailingScoreService.validar_cpf("") is False


# ── Validação de telefone ───────────────────────────────────
def test_validar_telefone_ok():
    assert MailingScoreService.validar_telefone("(11) 98888-7777") == "11988887777"
    assert MailingScoreService.validar_telefone("11 3333-4444") == "1133334444"


def test_validar_telefone_invalido():
    assert MailingScoreService.validar_telefone("00 1234-5678") is None  # DDD inválido
    assert MailingScoreService.validar_telefone("123") is None           # curto
    assert MailingScoreService.validar_telefone(None) is None


# ── Conversão de horário ────────────────────────────────────
def test_str_para_time():
    assert _str_para_time("09:30") == dtime(9, 30)
    assert _str_para_time("lixo") == dtime(8, 0)  # fallback


# ── Score de mailing ────────────────────────────────────────
def test_calcular_score_dentro_do_intervalo():
    row = pd.Series({
        "cpf": "52998224725",
        "telefone": "11988887777",
        "previous_cpc": 0.5,
        "days_delay": 10,
        "faixa_atraso_dias": 45,
        "melhor_hora_inicio": 0,
        "melhor_hora_fim": 23,
        "ddd": "11",
    })
    score = MailingScoreService.calcular_score(row)
    assert 0.0 <= score <= 100.0


def test_calcular_score_sem_colunas_obrigatorias():
    assert MailingScoreService.calcular_score(pd.Series({"foo": 1})) == 0.0


# ── Cálculo de pacing ───────────────────────────────────────
def test_calcular_pacing_respeita_limites():
    novo, motivo = PacingService._calcular_pacing(
        ocupacao_pct=100, abandono_pct=0, pacing_min=1.0, pacing_max=8.0
    )
    assert 1.0 <= novo <= 8.0
    assert motivo == "ajuste_proporcional"


def test_calcular_pacing_abandono_alto():
    novo, motivo = PacingService._calcular_pacing(
        ocupacao_pct=50, abandono_pct=99, pacing_min=1.0, pacing_max=8.0
    )
    assert motivo == "abandono_alto"
    assert 1.0 <= novo <= 8.0
