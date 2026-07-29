"""Rotas de autenticação."""
from __future__ import annotations

from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, Request, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.database import get_db
from app.core.deps import get_current_user
from app.core import ratelimit
from app.core.security import create_access_token, verify_password
from app.models.user import User
from app.schemas.auth import LoginRequest, TokenResponse, TokenUser
from app.services import audit

router = APIRouter(prefix="/api/auth", tags=["Autenticação"])


def _client_ip(request: Request | None) -> str:
    if request and request.client:
        return request.client.host
    return "unknown"


def _authenticate(
    db: Session, email: str, password: str, request: Request | None = None
) -> User:
    email = email.lower().strip()
    # Chave de rate-limit por e-mail + IP (mitiga brute-force sem enumerar usuários).
    rl_key = f"{email}:{_client_ip(request)}"
    if ratelimit.is_locked(
        rl_key, settings.LOGIN_MAX_ATTEMPTS, settings.LOGIN_LOCKOUT_SECONDS
    ):
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Muitas tentativas de login. Tente novamente mais tarde.",
            headers={"Retry-After": str(settings.LOGIN_LOCKOUT_SECONDS)},
        )

    user = db.scalar(select(User).where(User.email == email))
    if not user or not verify_password(password, user.hashed_password):
        ratelimit.record_failure(rl_key)
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="E-mail ou senha incorretos.",
        )
    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, detail="Usuário inativo."
        )
    ratelimit.reset(rl_key)
    user.last_login_at = datetime.now(timezone.utc)
    db.commit()
    return user


def _to_token_user(user: User) -> TokenUser:
    return TokenUser(
        id=user.id,
        email=user.email,
        full_name=user.full_name,
        role=user.role,
        sectors=[sa.sector for sa in user.sector_accesses],
    )


@router.post("/login", response_model=TokenResponse)
def login(payload: LoginRequest, request: Request, db: Session = Depends(get_db)):
    """Login via JSON (usado pelo front-end)."""
    user = _authenticate(db, payload.email, payload.password, request)
    token = create_access_token(user.id, {"role": user.role})
    audit.record(db, action="auth.login", entity="user", entity_id=user.id,
                 actor=user, request=request)
    return TokenResponse(
        access_token=token,
        expires_in_minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES,
    )


@router.post("/token", response_model=TokenResponse)
def token(
    request: Request,
    form: OAuth2PasswordRequestForm = Depends(),
    db: Session = Depends(get_db),
):
    """Endpoint OAuth2 (compatível com o botão Authorize do Swagger)."""
    user = _authenticate(db, form.username, form.password, request)
    access = create_access_token(user.id, {"role": user.role})
    return TokenResponse(
        access_token=access, expires_in_minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES
    )


@router.get("/me", response_model=TokenUser)
def me(user: User = Depends(get_current_user)):
    return _to_token_user(user)
