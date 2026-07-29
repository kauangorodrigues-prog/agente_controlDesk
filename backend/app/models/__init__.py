"""Registro central dos modelos ORM.

Importar tudo aqui garante que a metadata do SQLAlchemy conheça todas as
tabelas ao chamar Base.metadata.create_all().
"""
from app.models.user import User  # noqa: F401
from app.models.access import SectorAccess  # noqa: F401
from app.models.debtor import Debtor  # noqa: F401
from app.models.debt import Debt  # noqa: F401
from app.models.payment import Payment, PaymentAgreement  # noqa: F401
from app.models.control_desk import Campaign, PacingSnapshot  # noqa: F401
from app.models.planning import Forecast, Goal  # noqa: F401
from app.models.infra import Incident, SystemHealthCheck  # noqa: F401
from app.models.devops import Feature, Deployment  # noqa: F401
from app.models.audit import AuditLog  # noqa: F401
from app.models.lgpd import ConsentRecord, DataSubjectRequest  # noqa: F401

__all__ = [
    "User",
    "SectorAccess",
    "Debtor",
    "Debt",
    "Payment",
    "PaymentAgreement",
    "Campaign",
    "PacingSnapshot",
    "Forecast",
    "Goal",
    "Incident",
    "SystemHealthCheck",
    "Feature",
    "Deployment",
    "AuditLog",
    "ConsentRecord",
    "DataSubjectRequest",
]
