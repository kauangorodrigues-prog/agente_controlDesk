"""Gestão de usuários (cadastro de diretoria, gerência e administração)."""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.deps import get_current_user, require_role
from app.core.rbac import Role
from app.core.security import hash_password
from app.models.access import SectorAccess
from app.models.user import User
from app.schemas.user import UserCreate, UserOut, UserUpdate
from app.services import audit

router = APIRouter(prefix="/api/users", tags=["Usuários"])


def _serialize(user: User) -> UserOut:
    return UserOut(
        id=user.id,
        full_name=user.full_name,
        email=user.email,
        role=Role(user.role),
        is_active=user.is_active,
        sectors=[sa.sector for sa in user.sector_accesses],
        last_login_at=user.last_login_at,
        created_at=user.created_at,
    )


@router.get("", response_model=list[UserOut])
def list_users(
    db: Session = Depends(get_db),
    _: User = Depends(require_role(Role.GERENCIA)),
):
    users = db.scalars(select(User).order_by(User.full_name)).all()
    return [_serialize(u) for u in users]


@router.post("", response_model=UserOut, status_code=status.HTTP_201_CREATED)
def create_user(
    payload: UserCreate,
    request: Request,
    db: Session = Depends(get_db),
    actor: User = Depends(require_role(Role.GERENCIA)),
):
    email = payload.email.lower().strip()
    if db.scalar(select(User).where(User.email == email)):
        raise HTTPException(status.HTTP_409_CONFLICT, "E-mail já cadastrado.")

    user = User(
        full_name=payload.full_name.strip(),
        email=email,
        hashed_password=hash_password(payload.password),
        role=payload.role.value,
    )
    for sector in payload.sectors:
        user.sector_accesses.append(SectorAccess(sector=sector.value))
    db.add(user)
    db.commit()
    db.refresh(user)
    audit.record(db, action="user.create", entity="user", entity_id=user.id,
                 actor=actor, request=request, detail=f"role={user.role}")
    return _serialize(user)


@router.get("/{user_id}", response_model=UserOut)
def get_user(
    user_id: int,
    db: Session = Depends(get_db),
    actor: User = Depends(get_current_user),
):
    # usuário pode ver a si mesmo; gerência+ vê qualquer um
    if actor.id != user_id and actor.role == Role.ADMINISTRACAO.value:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Acesso negado.")
    user = db.get(User, user_id)
    if not user:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Usuário não encontrado.")
    return _serialize(user)


@router.patch("/{user_id}", response_model=UserOut)
def update_user(
    user_id: int,
    payload: UserUpdate,
    request: Request,
    db: Session = Depends(get_db),
    actor: User = Depends(require_role(Role.GERENCIA)),
):
    user = db.get(User, user_id)
    if not user:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Usuário não encontrado.")

    if payload.full_name is not None:
        user.full_name = payload.full_name.strip()
    if payload.role is not None:
        user.role = payload.role.value
    if payload.is_active is not None:
        user.is_active = payload.is_active
    if payload.password is not None:
        user.hashed_password = hash_password(payload.password)
    if payload.sectors is not None:
        user.sector_accesses.clear()
        for sector in payload.sectors:
            user.sector_accesses.append(SectorAccess(sector=sector.value))

    db.commit()
    db.refresh(user)
    audit.record(db, action="user.update", entity="user", entity_id=user.id,
                 actor=actor, request=request)
    return _serialize(user)


@router.delete("/{user_id}", status_code=status.HTTP_204_NO_CONTENT)
def deactivate_user(
    user_id: int,
    request: Request,
    db: Session = Depends(get_db),
    actor: User = Depends(require_role(Role.DIRETORIA)),
):
    user = db.get(User, user_id)
    if not user:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Usuário não encontrado.")
    if user.id == actor.id:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Não é possível desativar a si mesmo.")
    # Soft delete: preserva trilha de auditoria.
    user.is_active = False
    db.commit()
    audit.record(db, action="user.deactivate", entity="user", entity_id=user.id,
                 actor=actor, request=request)
