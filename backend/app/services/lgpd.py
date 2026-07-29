"""Serviço LGPD: exportação (portabilidade/acesso) e anonimização de dados."""
from __future__ import annotations

import hashlib
from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.debt import Debt
from app.models.debtor import Debtor
from app.models.lgpd import ConsentRecord
from app.models.payment import Payment


def export_debtor_data(db: Session, debtor: Debtor) -> dict:
    """Gera um relatório completo dos dados do titular (art. 18, I e V).

    Usado tanto para o direito de ACESSO quanto de PORTABILIDADE.
    """
    debts = db.scalars(select(Debt).where(Debt.debtor_id == debtor.id)).all()
    consents = db.scalars(
        select(ConsentRecord).where(ConsentRecord.debtor_id == debtor.id)
    ).all()

    debts_payload = []
    for d in debts:
        payments = db.scalars(select(Payment).where(Payment.debt_id == d.id)).all()
        debts_payload.append(
            {
                "contract_ref": d.contract_ref,
                "portfolio": d.portfolio,
                "creditor": d.creditor,
                "original_amount": d.original_amount,
                "current_amount": d.current_amount,
                "status": d.status,
                "payments": [
                    {"amount": p.amount, "method": p.method, "paid_at": str(p.paid_at)}
                    for p in payments
                ],
            }
        )

    return {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "titular": {
            "nome": debtor.full_name,
            "documento": debtor.document,
            "email": debtor.email,
            "telefone": debtor.phone,
            "cidade": debtor.city,
            "uf": debtor.state,
        },
        "dividas": debts_payload,
        "consentimentos": [
            {
                "finalidade": c.purpose,
                "base_legal": c.legal_basis,
                "concedido": c.granted,
                "em": c.granted_at.isoformat() if c.granted_at else None,
            }
            for c in consents
        ],
    }


def anonymize_debtor(db: Session, debtor: Debtor) -> None:
    """Anonimiza dados pessoais preservando integridade financeira/contábil.

    A LGPD (art. 16) permite conservar dados para cumprimento de obrigação
    legal/regulatória e exercício de direitos em processo. Por isso a dívida
    é mantida (base legal), mas todo PII identificável é irreversivelmente
    substituído por um pseudônimo derivado de hash.
    """
    token = hashlib.sha256(
        f"{debtor.id}:{debtor.document}:{datetime.now(timezone.utc)}".encode()
    ).hexdigest()[:12]

    debtor.full_name = f"TITULAR-ANONIMIZADO-{token}"
    debtor.document = f"ANON{token}"
    debtor.email = None
    debtor.phone = None
    debtor.city = None
    debtor.state = None
    debtor.is_anonymized = True
    debtor.anonymized_at = datetime.now(timezone.utc)
    db.commit()
