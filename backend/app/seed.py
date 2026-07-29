"""Popula o banco com dados iniciais realistas para testes e demonstração.

Uso:
    python -m app.seed

O seed é idempotente: pode ser executado várias vezes sem duplicar dados.
"""
from __future__ import annotations

import random
from datetime import date, datetime, timedelta, timezone

from sqlalchemy import func, select

from app.core.config import settings
from app.core.crypto import blind_index
from app.core.database import SessionLocal, init_db
from app.core.rbac import Role, Sector
from app.core.security import hash_password
from app.models.access import SectorAccess
from app.models.control_desk import Campaign, PacingSnapshot
from app.models.debt import Debt
from app.models.debtor import Debtor
from app.models.devops import Deployment, Feature
from app.models.infra import Incident, SystemHealthCheck
from app.models.interaction import Interaction
from app.models.lgpd import ConsentRecord, DataSubjectRequest
from app.models.payment import Payment, PaymentAgreement
from app.models.planning import Forecast, Goal
from app.models.user import User
from app.services.scoring import recovery_score

PORTFOLIOS = ["ativa", "consignado", "concierge", "bancario"]
CREDITORS = {
    "ativa": "Prefeitura Municipal de São Paulo",
    "consignado": "Banco Consignado Brasil S.A.",
    "concierge": "Concierge Premium Card",
    "bancario": "Banco Nacional do Comércio S.A.",
}
FIRST = [
    "Maria", "João", "José", "Ana", "Pedro", "Lucas", "Julia", "Carlos",
    "Fernanda", "Rafael", "Beatriz", "Gabriel", "Camila", "Rodrigo", "Larissa",
    "Bruno", "Patrícia", "Thiago", "Aline", "Marcelo",
]
LAST = [
    "Silva", "Santos", "Oliveira", "Souza", "Lima", "Costa", "Pereira",
    "Almeida", "Ferreira", "Rodrigues", "Gomes", "Martins", "Araújo", "Barbosa",
]
CITIES = [
    ("São Paulo", "SP"), ("Rio de Janeiro", "RJ"), ("Belo Horizonte", "MG"),
    ("Curitiba", "PR"), ("Porto Alegre", "RS"), ("Salvador", "BA"),
    ("Recife", "PE"), ("Fortaleza", "CE"), ("Campinas", "SP"), ("Goiânia", "GO"),
]
STREETS = ["Rua das Flores", "Av. Brasil", "Rua XV de Novembro", "Av. Paulista",
           "Rua do Comércio", "Travessa São João", "Av. Getúlio Vargas"]
NEIGHBORHOODS = ["Centro", "Jardim América", "Vila Nova", "Bela Vista", "Santa Cecília"]

INTERACTION_RESULTS = [
    "cpc", "cpca", "promessa", "recado", "sem_contato",
    "numero_errado", "nao_atende", "acordo_fechado",
]
INTERACTION_CHANNELS = ["telefone", "sms", "email", "whatsapp", "discador"]
NOTES_BY_RESULT = {
    "cpc": "Contato realizado, cliente ciente do débito.",
    "cpca": "Cliente aceitou proposta de negociação.",
    "promessa": "Cliente prometeu pagamento para a data acordada.",
    "recado": "Recado deixado com familiar.",
    "sem_contato": "Sem êxito no contato.",
    "numero_errado": "Número não pertence ao titular.",
    "nao_atende": "Chamada não atendida.",
    "acordo_fechado": "Acordo formalizado com o cliente.",
}


# ── Geração de CPF válido (dígitos verificadores corretos) ───────────────
def _cpf(rng: random.Random) -> str:
    base = [rng.randint(0, 9) for _ in range(9)]

    def _dv(nums: list[int]) -> int:
        s = sum(v * w for v, w in zip(nums, range(len(nums) + 1, 1, -1)))
        r = (s * 10) % 11
        return 0 if r == 10 else r

    d1 = _dv(base)
    d2 = _dv(base + [d1])
    return "".join(map(str, base + [d1, d2]))


def seed_users(db) -> User:
    """Cria usuários de exemplo cobrindo todos os papéis e setores."""
    users_spec = [
        (settings.FIRST_ADMIN_EMAIL, "Administrador Master", settings.FIRST_ADMIN_PASSWORD,
         Role.DIRETORIA, list(Sector)),
        ("diretoria@controldesk.example.com", "Ana Diretora", "Diretoria@123",
         Role.DIRETORIA, list(Sector)),
        ("gerencia@controldesk.example.com", "Bruno Gerente", "Gerencia@123",
         Role.GERENCIA, [Sector.CONTROL_DESK, Sector.PLANEJAMENTO, Sector.MIS]),
        ("operacao@controldesk.example.com", "Carla Administrativa", "Operacao@123",
         Role.ADMINISTRACAO, [Sector.CONTROL_DESK]),
        ("mis@controldesk.example.com", "Diego Analista MIS", "Mis@12345",
         Role.ADMINISTRACAO, [Sector.MIS, Sector.PLANEJAMENTO]),
        ("devops@controldesk.example.com", "Eduarda Engenheira", "Devops@123",
         Role.GERENCIA, [Sector.DESENVOLVIMENTO, Sector.INFRAESTRUTURA]),
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


def seed_collection(db, operator_id: int) -> None:
    if db.scalar(select(Debtor).limit(1)):
        return  # já populado

    rng = random.Random(42)

    for i in range(60):
        city, state = rng.choice(CITIES)
        birth = date.today() - timedelta(days=rng.randint(21 * 365, 70 * 365))
        cpf = _cpf(rng)
        debtor = Debtor(
            document=cpf,
            document_hash=blind_index(cpf),
            person_type="PF",
            full_name=f"{rng.choice(FIRST)} {rng.choice(LAST)} {rng.choice(LAST)}",
            email=f"titular{i:03d}@example.com",
            phone=f"({rng.randint(11, 98)}) 9{rng.randint(1000, 9999)}-{rng.randint(1000, 9999)}",
            phone_alt=f"({rng.randint(11, 98)}) {rng.randint(2000, 5999)}-{rng.randint(1000, 9999)}",
            birth_date=birth,
            zip_code=f"{rng.randint(10000, 99999)}-{rng.randint(100, 999)}",
            address=f"{rng.choice(STREETS)}, {rng.randint(1, 2000)}",
            neighborhood=rng.choice(NEIGHBORHOODS),
            city=city,
            state=state,
            contact_status="sem_contato",
        )
        db.add(debtor)
        db.flush()

        # Consentimento / base legal (varia por titular)
        db.add(ConsentRecord(
            debtor_id=debtor.id,
            purpose=rng.choice(["cobranca", "comunicacao", "score"]),
            legal_basis=rng.choice(
                ["legitimo_interesse", "execucao_contrato", "obrigacao_legal"]
            ),
            granted=True,
            channel=rng.choice(["sistema", "telefone", "web"]),
        ))

        debtor_debts: list[Debt] = []
        for _ in range(rng.randint(1, 3)):
            portfolio = rng.choice(PORTFOLIOS)
            original = round(rng.uniform(500, 50000), 2)
            days = rng.randint(5, 900)
            current = round(original * rng.uniform(1.0, 2.4), 2)
            debt = Debt(
                debtor_id=debtor.id,
                contract_ref=f"CT-{rng.randint(100000, 999999)}",
                portfolio=portfolio,
                creditor=CREDITORS[portfolio],
                original_amount=original,
                current_amount=current,
                due_date=date.today() - timedelta(days=days),
                days_overdue=days,
                status="pendente",
            )
            debt.risk_score = recovery_score(
                portfolio=portfolio, days_overdue=days,
                original_amount=original, current_amount=current,
            )
            db.add(debt)
            db.flush()
            debtor_debts.append(debt)

        # ── Histórico de contatos (tabulação) ────────────────────────
        n_inter = rng.randint(0, 5)
        last_result = "sem_contato"
        for k in range(n_inter):
            result = rng.choice(INTERACTION_RESULTS)
            last_result = result
            when = datetime.now(timezone.utc) - timedelta(days=rng.randint(0, 60),
                                                           hours=rng.randint(0, 23))
            target_debt = rng.choice(debtor_debts) if debtor_debts else None
            inter = Interaction(
                debtor_id=debtor.id,
                debt_id=target_debt.id if target_debt else None,
                channel=rng.choice(INTERACTION_CHANNELS),
                result=result,
                notes=NOTES_BY_RESULT[result],
                created_by=operator_id,
                created_at=when,
            )
            if result == "promessa" and target_debt:
                inter.promise_amount = round(target_debt.current_amount * 0.5, 2)
                inter.promise_date = date.today() + timedelta(days=rng.randint(2, 15))
                target_debt.status = "negociacao"
            db.add(inter)
        debtor.contact_status = last_result

        # ── Acordos e pagamentos (recuperação) ───────────────────────
        for debt in debtor_debts:
            roll = rng.random()
            if roll < 0.20:  # dívida quitada
                pay = Payment(debt_id=debt.id, amount=debt.current_amount,
                              method=rng.choice(["pix", "boleto", "cartao"]),
                              paid_at=date.today() - timedelta(days=rng.randint(1, 40)))
                db.add(pay)
                debt.current_amount = 0.0
                debt.status = "quitada"
            elif roll < 0.40:  # acordo em andamento
                installments = rng.choice([1, 3, 6, 12])
                discount = rng.choice([0, 10, 15, 20])
                net = debt.current_amount * (1 - discount / 100)
                db.add(PaymentAgreement(
                    debt_id=debt.id,
                    total_amount=debt.current_amount,
                    installments=installments,
                    installment_amount=round(net / installments, 2),
                    discount_pct=discount,
                    created_by=operator_id,
                ))
                debt.status = "acordo"
                # pagamento parcial de entrada
                entrada = round(net / installments, 2)
                db.add(Payment(debt_id=debt.id, amount=entrada, method="pix",
                               paid_at=date.today() - timedelta(days=rng.randint(1, 20))))
                debt.current_amount = round(debt.current_amount - entrada, 2)

    db.commit()


def seed_lgpd_requests(db) -> None:
    if db.scalar(select(DataSubjectRequest).limit(1)):
        return
    rng = random.Random(7)
    sample_debtors = db.scalars(select(Debtor).limit(6)).all()
    specs = [
        ("acesso", "concluida", "Titular solicitou cópia dos dados. Relatório enviado."),
        ("exclusao", "em_analise", "Em avaliação de obrigação legal de retenção."),
        ("correcao", "concluida", "Telefone corrigido conforme solicitação."),
        ("portabilidade", "recebida", "Aguardando validação de identidade."),
        ("revogacao", "concluida", "Consentimento de comunicação revogado."),
        ("anonimizacao", "recusada", "Retenção obrigatória por 5 anos (obrigação legal)."),
    ]
    for idx, (rtype, status_, note) in enumerate(specs):
        debtor = sample_debtors[idx] if idx < len(sample_debtors) else None
        created = datetime.now(timezone.utc) - timedelta(days=rng.randint(1, 30))
        resolved = None
        if status_ in ("concluida", "recusada"):
            resolved = created + timedelta(days=rng.randint(1, 5))
        db.add(DataSubjectRequest(
            debtor_id=debtor.id if debtor else None,
            requester_document=debtor.document if debtor else _cpf(rng),
            request_type=rtype,
            status=status_,
            notes=note,
            created_at=created,
            resolved_at=resolved,
        ))
    db.commit()


def seed_sectors(db) -> None:
    rng = random.Random(99)
    if not db.scalar(select(Campaign).limit(1)):
        for p in PORTFOLIOS:
            campaign = Campaign(
                name=f"Campanha {p.title()}", portfolio=p, is_active=True,
                pacing=round(rng.uniform(1.5, 4.0), 1),
                agents_online=rng.randint(8, 45),
                mailing_total=rng.randint(2000, 9000),
                mailing_worked=rng.randint(300, 1800),
            )
            db.add(campaign)
            db.flush()
            # Snapshots operacionais das últimas horas
            for h in range(6):
                db.add(PacingSnapshot(
                    campaign_id=campaign.id,
                    idle_pct=round(rng.uniform(3, 18), 1),
                    abandon_pct=round(rng.uniform(1, 9), 1),
                    calls_made=rng.randint(200, 1200),
                    contacts=rng.randint(50, 400),
                    promises=rng.randint(5, 60),
                    captured_at=datetime.now(timezone.utc) - timedelta(hours=h),
                ))

    if not db.scalar(select(Forecast).limit(1)):
        base = date.today().replace(day=1)
        for m in range(3):  # mês atual + 2 anteriores
            month = (base - timedelta(days=30 * m)).strftime("%Y-%m")
            for p in PORTFOLIOS:
                db.add(Forecast(
                    reference_month=month, portfolio=p,
                    expected_recovery=round(rng.uniform(100000, 900000), 2),
                    expected_volume=rng.randint(500, 3000),
                    assumptions="Baseline histórico + sazonalidade + capacidade instalada",
                ))
                target = round(rng.uniform(200000, 1000000), 2)
                db.add(Goal(
                    reference_month=month, portfolio=p,
                    target_amount=target,
                    achieved_amount=round(target * rng.uniform(0.4, 1.1), 2),
                ))

    if not db.scalar(select(Feature).limit(1)):
        features = [
            ("Integração com discador Olos", "em_andamento", "alta", "plataforma"),
            ("Dashboard de recuperação em tempo real", "review", "media", "dados"),
            ("Régua de comunicação por WhatsApp", "backlog", "alta", "canais"),
            ("Motor de score de mailing v2", "backlog", "media", "dados"),
            ("Exportação LGPD automatizada", "concluido", "alta", "plataforma"),
            ("SSO corporativo (SAML)", "em_andamento", "media", "plataforma"),
        ]
        for title, st, prio, squad in features:
            db.add(Feature(title=title, status=st, priority=prio, squad=squad))
        deploys = [
            ("1.0.0", "production", "sucesso"),
            ("1.1.0-rc1", "staging", "sucesso"),
            ("1.0.3", "production", "rollback"),
        ]
        for ver, env, st in deploys:
            db.add(Deployment(version=ver, environment=env, status=st,
                              deployed_at=datetime.now(timezone.utc)
                              - timedelta(days=rng.randint(1, 30))))

    if not db.scalar(select(Incident).limit(1)):
        db.add(Incident(title="Latência elevada no gateway de pagamentos",
                        severity="alta", status="investigando", service="payments",
                        description="P95 acima de 800ms no provedor PIX."))
        resolved = Incident(title="Fila de discagem travada", severity="critica",
                            status="resolvido", service="dialer",
                            description="Reinício do worker resolveu o backlog.")
        resolved.resolved_at = datetime.now(timezone.utc) - timedelta(hours=3)
        db.add(resolved)
        for svc in ["api", "db", "payments", "dialer", "frontend"]:
            db.add(SystemHealthCheck(
                service=svc,
                status=rng.choice(["up", "up", "up", "degraded"]),
                latency_ms=round(rng.uniform(10, 250), 1),
                cpu_pct=round(rng.uniform(10, 78), 1),
                mem_pct=round(rng.uniform(20, 85), 1),
            ))
    db.commit()


def main() -> None:
    init_db()
    db = SessionLocal()
    try:
        master = seed_users(db)
        operator = db.scalar(
            select(User).where(User.email == "operacao@controldesk.example.com")
        )
        seed_collection(db, operator.id if operator else master.id)
        seed_lgpd_requests(db)
        seed_sectors(db)

        n_debtors = db.scalar(select(func.count(Debtor.id)))
        n_debts = db.scalar(select(func.count(Debt.id)))
        n_inter = db.scalar(select(func.count(Interaction.id)))
        n_pay = db.scalar(select(func.count(Payment.id)))
        n_dsr = db.scalar(select(func.count(DataSubjectRequest.id)))

        print("✓ Seed concluído.")
        print(f"  Devedores: {n_debtors} · Dívidas: {n_debts} · "
              f"Contatos: {n_inter} · Pagamentos: {n_pay} · Requisições LGPD: {n_dsr}")
        print(f"  Login master: {master.email} / (senha em FIRST_ADMIN_PASSWORD)")
        print("  Usuários demo:")
        print("    diretoria@controldesk.example.com / Diretoria@123 (diretoria)")
        print("    gerencia@controldesk.example.com  / Gerencia@123  (gerência)")
        print("    operacao@controldesk.example.com  / Operacao@123  (administração)")
        print("    mis@controldesk.example.com       / Mis@12345     (MIS/Planejamento)")
        print("    devops@controldesk.example.com    / Devops@123    (Dev/Infra)")
    finally:
        db.close()


if __name__ == "__main__":
    main()
