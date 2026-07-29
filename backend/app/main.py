"""Ponto de entrada da API — ControlDesk Cobranças SaaS."""
from __future__ import annotations

import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.core.config import settings
from app.core.database import init_db
from app.routers import (
    auth,
    collection,
    control_desk,
    desenvolvimento,
    infraestrutura,
    lgpd,
    mis,
    planejamento,
    users,
)

logging.basicConfig(
    level=logging.DEBUG if settings.DEBUG else logging.INFO,
    format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
)
logger = logging.getLogger("controldesk")


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("Iniciando %s v%s (%s)", settings.APP_NAME, settings.APP_VERSION,
                settings.APP_ENV)
    init_db()
    yield
    logger.info("Encerrando aplicação.")


app = FastAPI(
    title=settings.APP_NAME,
    version=settings.APP_VERSION,
    description=(
        "SaaS completo de cobrança de dívidas (ativas, consignados, concierge e "
        "bancárias) com setores de Control Desk, Planejamento, MIS, Desenvolvimento "
        "e Infraestrutura, RBAC e conformidade LGPD."
    ),
    lifespan=lifespan,
    docs_url="/docs",
    redoc_url="/redoc",
    openapi_url="/openapi.json",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# Cabeçalhos de segurança básicos em todas as respostas.
@app.middleware("http")
async def security_headers(request: Request, call_next):
    response = await call_next(request)
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "DENY"
    response.headers["Referrer-Policy"] = "no-referrer"
    response.headers["Permissions-Policy"] = "geolocation=(), microphone=()"
    return response


@app.exception_handler(Exception)
async def unhandled_exception_handler(request: Request, exc: Exception):
    logger.exception("Erro não tratado em %s", request.url.path)
    return JSONResponse(status_code=500, content={"detail": "Erro interno do servidor."})


# ── Rotas de saúde / raiz ────────────────────────────────────────────────
@app.get("/", tags=["Sistema"])
def root():
    return {
        "app": settings.APP_NAME,
        "version": settings.APP_VERSION,
        "environment": settings.APP_ENV,
        "docs": "/docs",
        "health": "/health",
    }


@app.get("/health", tags=["Sistema"])
def health():
    return {"status": "ok", "version": settings.APP_VERSION}


# ── Registro dos routers ─────────────────────────────────────────────────
app.include_router(auth.router)
app.include_router(users.router)
app.include_router(collection.router)
app.include_router(control_desk.router)
app.include_router(planejamento.router)
app.include_router(mis.router)
app.include_router(desenvolvimento.router)
app.include_router(infraestrutura.router)
app.include_router(lgpd.router)
