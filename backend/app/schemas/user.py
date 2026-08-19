from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, ConfigDict, EmailStr, Field, field_validator

from app.core.rbac import Role, Sector


class UserBase(BaseModel):
    full_name: str = Field(min_length=2, max_length=180)
    email: EmailStr
    role: Role = Role.ADMINISTRACAO


class UserCreate(UserBase):
    password: str = Field(min_length=8, max_length=128)
    sectors: list[Sector] = []

    @field_validator("password")
    @classmethod
    def strong_password(cls, v: str) -> str:
        if v.isalpha() or v.isdigit():
            raise ValueError("A senha deve combinar letras e números.")
        return v


class UserUpdate(BaseModel):
    full_name: str | None = Field(default=None, min_length=2, max_length=180)
    role: Role | None = None
    is_active: bool | None = None
    password: str | None = Field(default=None, min_length=8, max_length=128)
    sectors: list[Sector] | None = None


class UserOut(UserBase):
    model_config = ConfigDict(from_attributes=True)

    id: int
    is_active: bool
    sectors: list[str] = []
    last_login_at: datetime | None = None
    created_at: datetime
