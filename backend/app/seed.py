"""Popula o banco com dados iniciais para testes e demonstração.

Uso:
    python -m app.seed
"""
from __future__ import annotations

import random
from datetime import date, datetime, timedelta, timezone

from sqlalchemy import select

from app.core.config import settings
from app.core.database import SessionLocal, init_db
from app.core.rbac import Role, Sector
from app.core.security import hash_password
from app.models.access import SectorAccess
from app.models.control_desk import Campaign
from app.models.debt import Debt
from app.models.debtor import Debtor
from app.models.devops import Deployment, Feature
from app.models.infra import Incident, SystemHealthCheck
from app.models.lgpd import ConsentRecord
from app.models.planning import Forecast, Goal
from app.models.user import User
from app.services.scoring import recovery_score

PORTFOLIOS = ["ativa", "consignado", "concierge", "bancario"]
CREDITORS = {
    "ativa": "Prefeitura Municipal",
    "consignado": "Banco Consignado S.A.",
    "concierge": "Concierge Premium Card",
    "bancario": "Banco Nacional S.A.",
}


def _all_sectors() -> list[SectorAccess]:
    return [SectorAccess(sector=s.value) for s in Sector]


def seed_users(db) -> User:
    """Cria usuários de exemplo (um por papel) + admin master."""
    users_spec = [
        (settings.FIRST_ADMIN_EMAIL, "Administrador Master", settings.FIRST_ADMIN_PASSWORD,
         Role.DIRETORIA, list(Sector)),
        ("diretoria@controldesk.example.com", "Ana Diretora", "Diretoria@123",
         Role.DIRETORIA, list(Sector)),
        ("gerencia@controldesk.example.com", "Bruno Gerente", "Gerencia@123",
         Role.GERENCIA, [Sector.CONTROL_DESK, Sector.PLANEJAMENTO, Sector.MIS]),
        ("admin@controldesk.example.com".replace("admin@", "operacao@"),
         "Carla Administrativa", "Operacao@123",
         Role.ADMINISTRACAO, [Sector.CONTROL_DESK]),
    ]
    master = None
    for email, name, pwd, role, sectors in users_spec:
        existing = db.scalar(select(User).where(User.email == email))
        if existing:
            if master is None:
                master = existing
            continue
        user = User(
            full_name=name,
            email=email,
            hashed_password=hash_password(pwd),
            role=role.value,
            accepted_terms_at=datetime.now(timezone.utc),
        )
        for s in sectors:
            user.sector_accesses.append(SectorAccess(sector=s.value))
        db.add(user)
        if master is None:
            master = user
    db.commit()
    return master


def seed_collection(db) -> None:
    if db.scalar(select(Debtor).limit(1)):
        return  # já populado

    random.seed(42)
    first = ["Maria", "João", "José", "Ana", "Pedro", "Lucas", "Julia", "Carlos"]
    last = ["Silva", "Santos", "Oliveira", "Souza", "Lima", "Costa", "Pereira"]

    for i in range(40):
        doc = "".join(str(random.randint(0, 9)) for _ in range(11))
        debtor = Debtor(
            document=doc,
            full_name=f"{random.choice(first)} {random.choice(last)}",
            email=f"titular{i}@example.com",
            phone=f"11{random.randint(900000000, 999999999)}",
            city="São Paulo",
            state="SP",
        )
        db.add(debtor)
        db.flush()

        # Consentimento / base legal
        db.add(ConsentRecord(
            debtor_id=debtor.id, purpose="cobranca",
            legal_basis="legitimo_interesse", granted=True,
        ))

        for _ in range(random.randint(1, 3)):
            portfolio = random.choice(PORTFOLIOS)
            original = round(random.uniform(500, 50000), 2)
            days = random.randint(5, 720)
            current = round(original * random.uniform(1.0, 2.2), 2)
            debt = Debt(
                debtor_id=debtor.id,
                contract_ref=f"CT-{random.randint(100000, 999999)}",
                portfolio=portfolio,
                creditor=CREDITORS[portfolio],
                original_amount=original,
                current_amount=current,
                due_date=date.today() - timedelta(days=days),
                days_overdue=days,
                status=random.choice(["pendente", "pendente", "negociacao", "acordo"]),
            )
            debt.risk_score = recovery_score(
                portfolio=portfolio, days_overdue=days,
                original_amount=original, current_amount=current,
            )
            db.add(debt)
    db.commit()


def seed_sectors(db) -> None:
    if not db.scalar(select(Campaign).limit(1)):
        for p in PORTFOLIOS:
            db.add(Campaign(
                name=f"Campanha {p.title()}", portfolio=p, is_active=True,
                pacing=round(random.uniform(1.5, 4.0), 1),
                agents_online=random.randint(5, 40),
                mailing_total=random.randint(1000, 8000),
                mailing_worked=random.randint(100, 900),
            ))

    if not db.scalar(select(Forecast).limit(1)):
        month = date.today().strftime("%Y-%m")
        for p in PORTFOLIOS:
            db.add(Forecast(
                reference_month=month, portfolio=p,
                expected_recovery=round(random.uniform(100000, 900000), 2),
                expected_volume=random.randint(500, 3000),
                assumptions="Baseline histórico + sazonalidade",
            ))
            db.add(Goal(
                reference_month=month, portfolio=p,
                target_amount=round(random.uniform(200000, 1000000), 2),
                achieved_amount=round(random.uniform(50000, 800000), 2),
            ))

    if not db.scalar(select(Feature).limit(1)):
        db.add(Feature(title="Integração com discador Olos", status="em_andamento",
                       priority="alta", squad="plataforma"))
        db.add(Feature(title="Dashboard de recuperação em tempo real",
                       status="review", priority="media", squad="dados"))
        db.add(Deployment(version="1.0.0", environment="production", status="sucesso"))

    if not db.scalar(select(Incident).limit(1)):
        db.add(Incident(title="Latência elevada no gateway de pagamentos",
                        severity="alta", status="investigando", service="payments"))
        for svc in ["api", "db", "payments", "dialer"]:
            db.add(SystemHealthCheck(
                service=svc, status="up",
                latency_ms=round(random.uniform(10, 200), 1),
                cpu_pct=round(random.uniform(10, 70), 1),
                mem_pct=round(random.uniform(20, 80), 1),
            ))
    db.commit()


def main() -> None:
    init_db()
    db = SessionLocal()
    try:
        master = seed_users(db)
        seed_collection(db)
        seed_sectors(db)
        print("✓ Seed concluído.")
        print(f"  Login master: {master.email} / (senha definida em FIRST_ADMIN_PASSWORD)")
        print("  Usuários demo:")
        print("    diretoria@controldesk.example.com / Diretoria@123")
        print("    gerencia@controldesk.example.com  / Gerencia@123")
        print("    operacao@controldesk.example.com  / Operacao@123")
    finally:
        db.close()


if __name__ == "__main__":
    main()
