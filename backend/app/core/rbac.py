"""Controle de acesso baseado em papéis (RBAC) e definição de setores.

Papéis (cargos):
    - diretoria       : acesso total (visão executiva + gestão de usuários)
    - gerencia        : gestão operacional dos setores + relatórios
    - administracao   : cadastros, operação do dia a dia, LGPD

Setores/áreas da SaaS:
    - control_desk    : monitoramento operacional, pacing, mailing
    - planejamento    : forecast, metas, alocação de carteiras
    - mis             : relatórios, indicadores, BI
    - desenvolvimento : gestão de features, integrações, deploys
    - infraestrutura  : saúde de sistemas, incidentes, capacidade
"""
from __future__ import annotations

from enum import Enum


class Role(str, Enum):
    DIRETORIA = "diretoria"
    GERENCIA = "gerencia"
    ADMINISTRACAO = "administracao"


class Sector(str, Enum):
    CONTROL_DESK = "control_desk"
    PLANEJAMENTO = "planejamento"
    MIS = "mis"
    DESENVOLVIMENTO = "desenvolvimento"
    INFRAESTRUTURA = "infraestrutura"


# Hierarquia de papéis (maior número = mais privilégios).
ROLE_LEVEL: dict[Role, int] = {
    Role.ADMINISTRACAO: 1,
    Role.GERENCIA: 2,
    Role.DIRETORIA: 3,
}


def has_min_role(user_role: str, required: Role) -> bool:
    """True se o papel do usuário for >= ao papel exigido na hierarquia."""
    try:
        return ROLE_LEVEL[Role(user_role)] >= ROLE_LEVEL[required]
    except (KeyError, ValueError):
        return False


# Papéis que podem gerir usuários / conceder acessos.
USER_MANAGEMENT_ROLES = {Role.DIRETORIA, Role.GERENCIA}
