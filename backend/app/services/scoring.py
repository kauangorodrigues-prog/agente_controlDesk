"""Serviço de scoring de risco de recuperação de dívida.

Modelo heurístico transparente (explicável) — evita "caixa preta" e
facilita conformidade com o princípio de transparência da LGPD (art. 6º).
Score de 0 (baixíssima recuperação) a 100 (altíssima recuperação).
"""
from __future__ import annotations


PORTFOLIO_WEIGHT = {
    "consignado": 1.15,  # desconto em folha → maior recuperação
    "bancario": 1.0,
    "ativa": 0.9,
    "concierge": 1.05,
}


def recovery_score(
    *,
    portfolio: str,
    days_overdue: int,
    original_amount: float,
    current_amount: float,
) -> float:
    base = 70.0

    # Quanto maior o atraso, menor a probabilidade de recuperação.
    if days_overdue <= 30:
        base += 15
    elif days_overdue <= 90:
        base += 5
    elif days_overdue <= 180:
        base -= 5
    elif days_overdue <= 360:
        base -= 15
    else:
        base -= 25

    # Dívidas que já cresceram muito acima do original tendem a ser mais difíceis.
    if original_amount > 0:
        growth = current_amount / original_amount
        if growth > 2:
            base -= 10
        elif growth > 1.5:
            base -= 5

    base *= PORTFOLIO_WEIGHT.get(portfolio, 1.0)
    return round(max(0.0, min(100.0, base)), 1)
