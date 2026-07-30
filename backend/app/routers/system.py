"""Rotas de sistema: inicialização remota do banco (bootstrap pós-deploy).

O endpoint de bootstrap cria o schema e popula os dados iniciais uma única vez,
protegido por token. É idempotente: chamadas repetidas não duplicam dados.
Desabilitado quando BOOTSTRAP_TOKEN não está configurado.
"""
from __future__ import annotations

from fastapi import APIRouter, Header, HTTPException, status
from sqlalchemy import func, select

from app.core.config import settings
from app.core.database import SessionLocal, init_db
from app.models.debtor import Debtor
from app.models.user import User

router = APIRouter(prefix="/api/system", tags=["Sistema"])


@router.post("/bootstrap")
def bootstrap(x_bootstrap_token: str = Header(default="")):
    """Inicializa o banco (schema + seed). Uso único, protegido por token."""
    if not settings.BOOTSTRAP_TOKEN:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Bootstrap desabilitado.")
    if x_bootstrap_token != settings.BOOTSTRAP_TOKEN:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Token de bootstrap inválido.")

    # Cria o schema (idempotente) e popula os dados de demonstração.
    init_db()
    from app.seed import main as run_seed

    run_seed()

    db = SessionLocal()
    try:
        users = db.scalar(select(func.count(User.id))) or 0
        debtors = db.scalar(select(func.count(Debtor.id))) or 0
    finally:
        db.close()
    return {"ok": True, "users": users, "debtors": debtors}
