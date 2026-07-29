"""Schemas dos setores: Control Desk, Planejamento, Infra e Desenvolvimento."""
from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


# ── Control Desk ─────────────────────────────────────────────────────────
class CampaignCreate(BaseModel):
    name: str = Field(min_length=1, max_length=120)
    portfolio: str = Field(min_length=1, max_length=20)
    pacing: float = Field(default=2.0, ge=1.0, le=8.0)
    agents_online: int = Field(default=0, ge=0)
    mailing_total: int = Field(default=0, ge=0)


class CampaignOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    portfolio: str
    is_active: bool
    pacing: float
    agents_online: int
    mailing_total: int
    mailing_worked: int


# ── Planejamento ─────────────────────────────────────────────────────────
class ForecastCreate(BaseModel):
    reference_month: str = Field(pattern=r"^\d{4}-\d{2}$")
    portfolio: str
    expected_recovery: float = Field(ge=0)
    expected_volume: int = Field(ge=0)
    assumptions: str | None = None


class ForecastOut(ForecastCreate):
    model_config = ConfigDict(from_attributes=True)
    id: int
    created_at: datetime


class GoalCreate(BaseModel):
    reference_month: str = Field(pattern=r"^\d{4}-\d{2}$")
    portfolio: str
    target_amount: float = Field(ge=0)


class GoalOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    reference_month: str
    portfolio: str
    target_amount: float
    achieved_amount: float
    attainment_pct: float


# ── Infraestrutura ───────────────────────────────────────────────────────
class IncidentCreate(BaseModel):
    title: str = Field(min_length=1, max_length=160)
    description: str | None = None
    severity: str = Field(default="media", pattern="^(baixa|media|alta|critica)$")
    service: str = Field(default="core", max_length=80)


class IncidentOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    title: str
    description: str | None
    severity: str
    status: str
    service: str
    opened_at: datetime
    resolved_at: datetime | None


# ── Desenvolvimento ──────────────────────────────────────────────────────
class FeatureCreate(BaseModel):
    title: str = Field(min_length=1, max_length=160)
    description: str | None = None
    priority: str = Field(default="media", pattern="^(baixa|media|alta)$")
    squad: str = Field(default="plataforma", max_length=60)


class FeatureOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    title: str
    description: str | None
    status: str
    priority: str
    squad: str
    created_at: datetime
