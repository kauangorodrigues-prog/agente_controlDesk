"""Ponto de entrada da API — ControlDesk Cobranças SaaS."""
from __future__ import annotations

import logging
import time
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.core.config import settings
from app.core.database import init_db
from app.core.observability import (
    RequestIdFilter,
    metrics,
    new_request_id,
    request_id_ctx,
)
from app.routers import (
    auth,
    collection,
    control_desk,
    desenvolvimento,
    infraestrutura,
    lgpd,
    mis,
    notifications,
    planejamento,
    users,
)

logging.basicConfig(
    level=logging.DEBUG if settings.DEBUG else logging.INFO,
    format="%(asctime)s | %(levelname)s | %(name)s | req=%(request_id)s | %(message)s",
)
# Injeta o request_id em todos os logs (correlação de requisições).
for _handler in logging.getLogger().handlers:
    _handler.addFilter(RequestIdFilter())
logger = logging.getLogger("controldesk")


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("Iniciando %s v%s (%s)", settings.APP_NAME, settings.APP_VERSION,
                settings.APP_ENV)
    settings.validate_for_production()  # falha rápido com segredos inseguros
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


# Request-id, timing, métricas e cabeçalhos de segurança em todas as respostas.
@app.middleware("http")
async def security_headers(request: Request, call_next):
    request_id = request.headers.get("X-Request-ID") or new_request_id()
    token = request_id_ctx.set(request_id)
    started = time.perf_counter()
    try:
        response = await call_next(request)
    finally:
        request_id_ctx.reset(token)
    elapsed_ms = (time.perf_counter() - started) * 1000
    metrics.observe(request.method, response.status_code, elapsed_ms)
    response.headers["X-Request-ID"] = request_id
    response.headers["X-Response-Time-ms"] = f"{elapsed_ms:.1f}"
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "DENY"
    response.headers["Referrer-Policy"] = "no-referrer"
    response.headers["Permissions-Policy"] = "geolocation=(), microphone=()"
    if settings.is_production:
        response.headers["Strict-Transport-Security"] = (
            "max-age=31536000; includeSubDomains"
        )
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


@app.get("/metrics", tags=["Sistema"])
def get_metrics():
    """Métricas operacionais agregadas (uptime, volume, latência)."""
    return {"app": settings.APP_NAME, **metrics.snapshot()}


# ── Registro dos routers ─────────────────────────────────────────────────
app.include_router(auth.router)
app.include_router(users.router)
app.include_router(collection.router)
app.include_router(control_desk.router)
app.include_router(planejamento.router)
app.include_router(mis.router)
app.include_router(desenvolvimento.router)
app.include_router(infraestrutura.router)
app.include_router(notifications.router)
app.include_router(lgpd.router)
