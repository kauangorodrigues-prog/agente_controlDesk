"""Validadores puros (CPF, telefone) e utilitários de tempo.

Camada `utils`: sem dependências do restante da aplicação — totalmente testável
isoladamente.
"""
from __future__ import annotations

import re
from datetime import time as dtime
from typing import Optional

# DDDs válidos no Brasil (aproximação por faixas).
DDDS_VALIDOS = {
    str(d) for d in
    list(range(11, 20)) + list(range(21, 30)) +
    list(range(31, 40)) + list(range(41, 50)) +
    list(range(51, 70)) + list(range(71, 99))
}

# Peso de contatabilidade por DDD (usado no score heurístico e nas features).
DDD_SCORE_MAP = {
    "11": 10, "21": 9, "31": 8, "41": 8, "51": 7,
    "71": 7,  "61": 6, "85": 6, "81": 6,
}


def validar_cpf(cpf: str) -> bool:
    cpf = re.sub(r"\D", "", str(cpf or ""))
    if len(cpf) != 11 or len(set(cpf)) == 1:
        return False
    for i in range(2):
        soma = sum(int(cpf[j]) * (10 + i - j) for j in range(9 + i))
        if (soma * 10 % 11) % 10 != int(cpf[9 + i]):
            return False
    return True


def validar_telefone(tel: str) -> Optional[str]:
    digits = re.sub(r"\D", "", str(tel or ""))
    if len(digits) not in (10, 11):
        return None
    if digits[:2] not in DDDS_VALIDOS:
        return None
    return digits


def str_para_time(s: str) -> dtime:
    try:
        p = str(s).split(":")
        return dtime(int(p[0]), int(p[1]))
    except Exception:
        return dtime(8, 0)
