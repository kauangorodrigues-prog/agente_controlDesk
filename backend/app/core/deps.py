"""Dependencies de autenticação e autorização do FastAPI."""
from __future__ import annotations

from fastapi import Depends, HTTPException, Request, status
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.rbac import Role, Sector, has_min_role
from app.core.security import decode_token
from app.models.user import User

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/auth/token", auto_error=False)

_CREDENTIALS_EXC = HTTPException(
    status_code=status.HTTP_401_UNAUTHORIZED,
    detail="Credenciais inválidas ou expiradas.",
    headers={"WWW-Authenticate": "Bearer"},
)


def get_current_user(
    request: Request,
    token: str | None = Depends(oauth2_scheme),
    db: Session = Depends(get_db),
) -> User:
    if not token:
        raise _CREDENTIALS_EXC
    payload = decode_token(token)
    if not payload or payload.get("type") != "access":
        raise _CREDENTIALS_EXC
    try:
        user_id = int(payload["sub"])
    except (KeyError, ValueError):
        raise _CREDENTIALS_EXC

    user = db.get(User, user_id)
    if not user or not user.is_active:
        raise _CREDENTIALS_EXC
    # anexa ao request para uso na auditoria
    request.state.user = user
    return user


def require_role(minimum: Role):
    """Fábrica de dependency: exige papel mínimo na hierarquia."""

    def _dep(user: User = Depends(get_current_user)) -> User:
        if not has_min_role(user.role, minimum):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Acesso restrito ao papel '{minimum.value}' ou superior.",
            )
        return user

    return _dep


def require_sector(sector: Sector):
    """Exige que o usuário tenha acesso ao setor (diretoria acessa tudo)."""

    def _dep(user: User = Depends(get_current_user)) -> User:
        if user.role == Role.DIRETORIA.value:
            return user
        granted = {sa.sector for sa in user.sector_accesses}
        if sector.value not in granted:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Sem acesso ao setor '{sector.value}'.",
            )
        return user

    return _dep
