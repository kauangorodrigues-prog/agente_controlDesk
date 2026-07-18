"""Servidor standalone do robô Analisador de Ligações ALO / NÃO ALO.

Sobe **apenas** os endpoints de análise de qualidade de ligações, sem depender
do scheduler, do Postgres ou das libs de ML do restante do Control Desk — ideal
para rodar o "robô" isoladamente (por padrão na porta 5501).

    python main.py alo              # porta padrão 5501
    python main.py alo 8090         # porta customizada
    python -m control_desk.alo_server
    ROBO_ALO_PORT=5501 python -m control_desk.alo_server

Segurança (pronto para rodar na rede):
    ROBO_ALO_API_KEY        chave exigida no header X-API-Key em todas as rotas
                            /alo/*. Se não definida, uma chave forte é gerada e
                            registrada no log na inicialização (nunca fica aberto).
    ROBO_ALO_HOST           interface de escuta (padrão 0.0.0.0 — toda a rede).
    ROBO_ALO_CORS_ORIGINS   origens permitidas no navegador, separadas por vírgula
                            (padrão: nenhuma — cross-origin bloqueado).
    ROBO_ALO_RATE_LIMIT     requisições por minuto por IP (padrão 120).
    ROBO_ALO_MAX_LOTE       máximo de ligações por POST /alo/lote (padrão 1000).
    ROBO_ALO_MAX_BYTES      tamanho máximo do corpo em bytes (padrão 5 MB).
    ROBO_ALO_TLS_CERT/KEY   caminhos de certificado/chave para servir em HTTPS.

Sem ``ANTHROPIC_API_KEY`` (ou com ``ALO_USAR_IA=false``) roda 100% offline na
heurística. Sem Postgres, a análise ainda funciona — apenas não persiste.
"""
from __future__ import annotations

import os
import re
import secrets
import threading
import time
from collections import defaultdict, deque
from typing import Optional

from .config import CFG
from .logging_setup import get_logger

log = get_logger("alo_server")

# ── Configuração de segurança (lida do ambiente) ────────────────────────────
_API_KEY = os.getenv("ROBO_ALO_API_KEY", "").strip()
_API_KEY_GERADA = False
if not _API_KEY:
    _API_KEY = secrets.token_urlsafe(32)
    _API_KEY_GERADA = True

_RATE_LIMIT = max(1, int(os.getenv("ROBO_ALO_RATE_LIMIT", "120")))   # req/min por IP
_MAX_LOTE = max(1, int(os.getenv("ROBO_ALO_MAX_LOTE", "1000")))      # ligações por lote
_MAX_BYTES = max(1024, int(os.getenv("ROBO_ALO_MAX_BYTES", str(5 * 1024 * 1024))))
_CALL_ID_RE = re.compile(r"^[A-Za-z0-9_:-]{1,128}$")  # sem pontos/barras (anti path-traversal)

try:
    from fastapi import Depends, FastAPI, Header, HTTPException, Query, Request
    from fastapi.middleware.cors import CORSMiddleware
    from fastapi.responses import JSONResponse
    from pydantic import BaseModel

    from . import alo_store
    from .alo_analyzer import ANALISADOR
    from .alo_service import AloService

    def _backend_persistencia() -> str:
        return alo_store.backend()

    # ── Autenticação por API-key (comparação em tempo constante) ─────────────
    def requer_chave(x_api_key: str = Header(default="", alias="X-API-Key")) -> bool:
        if not x_api_key or not secrets.compare_digest(x_api_key, _API_KEY):
            raise HTTPException(status_code=401, detail="Chave de API ausente ou inválida.")
        return True

    _AUTH = [Depends(requer_chave)]

    # ── Modelos ──────────────────────────────────────────────────────────────
    class TurnoIn(BaseModel):
        falante: str = "cliente"
        texto: str = ""
        inicio_seg: Optional[float] = None

    class LoteIn(BaseModel):
        chamadas: list[dict] = []
        persistir: bool = True
        usar_ia: Optional[bool] = None

    class LigacaoIn(BaseModel):
        numero_chamado: str = ""
        numero_origem: str = ""
        data: str = ""
        hora: str = ""
        operadora: str = ""
        duracao_total_seg: float = 0.0
        tempo_ate_conexao_seg: float = 0.0
        tempo_fala_seg: float = 0.0
        tempo_silencio_seg: float = 0.0
        tempo_espera_seg: float = 0.0
        tempo_transferencia_seg: float = 0.0
        tempo_ate_primeiro_alo_seg: Optional[float] = None
        codigo_encerramento: str = ""
        causa_sip: str = ""
        amd: str = ""
        transferencia: bool = False
        transcricao: str = ""
        turnos: list[TurnoIn] = []
        usar_ia: Optional[bool] = None

    app = FastAPI(
        title="Robô Analisador de Ligações ALO / NÃO ALO",
        version="1.1.0",
        description="Avalia a qualidade da ligação entregue pela operadora ao discador.",
    )

    # CORS: só habilita se origens forem explicitamente configuradas.
    _origins = [o.strip() for o in os.getenv("ROBO_ALO_CORS_ORIGINS", "").split(",") if o.strip()]
    if _origins:
        app.add_middleware(
            CORSMiddleware, allow_origins=_origins,
            allow_methods=["GET", "POST"], allow_headers=["X-API-Key", "Content-Type"],
        )

    # ── Rate-limit por IP + limite de corpo + cabeçalhos de segurança ────────
    _hits: dict[str, deque] = defaultdict(deque)
    _rl_lock = threading.Lock()

    @app.middleware("http")
    async def _guardas(request: Request, call_next):
        # Tamanho do corpo
        cl = request.headers.get("content-length")
        if cl:
            try:
                if int(cl) > _MAX_BYTES:
                    return JSONResponse({"detail": "Corpo da requisição excede o limite."}, status_code=413)
            except ValueError:
                pass
        # Rate-limit (janela deslizante de 60s por IP)
        ip = request.client.host if request.client else "desconhecido"
        agora = time.time()
        with _rl_lock:
            dq = _hits[ip]
            while dq and agora - dq[0] > 60.0:
                dq.popleft()
            if len(dq) >= _RATE_LIMIT:
                return JSONResponse({"detail": "Limite de requisições excedido."}, status_code=429)
            dq.append(agora)
        resp = await call_next(request)
        resp.headers["X-Content-Type-Options"] = "nosniff"
        resp.headers["X-Frame-Options"] = "DENY"
        resp.headers["Referrer-Policy"] = "no-referrer"
        resp.headers["Cache-Control"] = "no-store"
        return resp

    # ── Rotas públicas (sem PII) ─────────────────────────────────────────────
    @app.get("/", tags=["Robô"])
    def raiz():
        ia_ativa = bool(CFG.ALO_USAR_IA and CFG.ANTHROPIC_API_KEY)
        return {
            "robo": "Analisador de Ligações ALO / NÃO ALO",
            "status": "online",
            "modo": "IA (Claude)" if ia_ativa else "heurística offline",
            "autenticacao": "obrigatória — header X-API-Key nas rotas /alo/*",
            "persistencia": _backend_persistencia(),
            "endpoints": [
                "POST /alo/analisar        (uma ligação, resposta imediata)",
                "POST /alo/lote            (lote de ligações no corpo, persiste)",
                "GET  /alo/call/{call_id}  (puxa do discador Olos)",
                "POST /alo/processar       (puxa lote recente do Olos)",
                "GET  /alo/historico",
                "GET  /alo/estatisticas",
                "GET  /docs",
            ],
        }

    @app.get("/health", tags=["Robô"])
    def health():
        return {"status": "ok"}

    # ── Rotas protegidas (exigem X-API-Key) ──────────────────────────────────
    @app.post("/alo/analisar", tags=["ALO"], dependencies=_AUTH)
    def analisar_ligacao(body: LigacaoIn):
        payload = body.dict()
        usar_ia = payload.pop("usar_ia", None)
        return ANALISADOR.analisar_dict(payload, usar_ia=usar_ia)

    @app.post("/alo/lote", tags=["ALO"], dependencies=_AUTH)
    def processar_lote_payload(body: LoteIn):
        if len(body.chamadas) > _MAX_LOTE:
            raise HTTPException(
                status_code=413,
                detail=f"Lote com {len(body.chamadas)} ligações excede o máximo de {_MAX_LOTE}.",
            )
        return AloService.processar_payload(
            body.chamadas, persistir=body.persistir, usar_ia=body.usar_ia
        )

    @app.get("/alo/call/{call_id}", tags=["ALO"], dependencies=_AUTH)
    def analisar_call(call_id: str, persistir: bool = Query(True), usar_ia: Optional[bool] = Query(None)):
        if not _CALL_ID_RE.match(call_id):
            raise HTTPException(status_code=400, detail="call_id inválido.")
        return AloService.analisar_call(call_id, persistir=persistir, usar_ia=usar_ia)

    @app.post("/alo/processar", tags=["ALO"], dependencies=_AUTH)
    def processar_alo(
        desde: Optional[str] = Query(None), limite: int = Query(200, ge=1, le=5000),
        persistir: bool = Query(True), usar_ia: Optional[bool] = Query(None),
    ):
        return AloService.processar_lote(desde=desde, limite=limite, persistir=persistir, usar_ia=usar_ia)

    @app.get("/alo/historico", tags=["ALO"], dependencies=_AUTH)
    def historico_alo(
        limite: int = Query(100, ge=1, le=1000), classificacao: Optional[str] = Query(None),
        operadora: Optional[str] = Query(None),
    ):
        return AloService.historico(limite=limite, classificacao=classificacao, operadora=operadora)

    @app.get("/alo/estatisticas", tags=["ALO"], dependencies=_AUTH)
    def estatisticas_alo(dias: int = Query(1, ge=1, le=365)):
        return AloService.estatisticas(dias=dias)

    FASTAPI_DISPONIVEL = True

except ImportError as _e:
    log.error(f"FastAPI/uvicorn não instalados — robô ALO indisponível: {_e}")
    app = None
    FASTAPI_DISPONIVEL = False


def porta_padrao() -> int:
    return int(os.getenv("ROBO_ALO_PORT", "5501"))


def _log_seguranca() -> None:
    if _API_KEY_GERADA:
        log.warning("=" * 68)
        log.warning("ROBO_ALO_API_KEY não definida — chave gerada para esta sessão:")
        log.warning("    X-API-Key: %s", _API_KEY)
        log.warning("Defina ROBO_ALO_API_KEY no ambiente para fixar a chave.")
        log.warning("=" * 68)
    else:
        log.info("Autenticação por API-key ativa (ROBO_ALO_API_KEY do ambiente).")


def run(port: Optional[int] = None, host: Optional[str] = None) -> None:
    """Sobe o robô ALO com as proteções ativas.

    Porta: argumento > ROBO_ALO_PORT > 5501. Host: ROBO_ALO_HOST > 0.0.0.0.
    HTTPS automático se ROBO_ALO_TLS_CERT e ROBO_ALO_TLS_KEY estiverem definidos.
    """
    if app is None:
        raise RuntimeError(
            "FastAPI/uvicorn não instalados. Rode: pip install fastapi 'uvicorn[standard]'"
        )
    import uvicorn

    porta = port or porta_padrao()
    host = host or os.getenv("ROBO_ALO_HOST", "0.0.0.0")
    ssl_kwargs: dict = {}
    cert, key = os.getenv("ROBO_ALO_TLS_CERT"), os.getenv("ROBO_ALO_TLS_KEY")
    if cert and key:
        ssl_kwargs = {"ssl_certfile": cert, "ssl_keyfile": key}
        esquema = "https"
    else:
        esquema = "http"

    _log_seguranca()
    log.info(f"🤖 Robô Analisador ALO ouvindo em {esquema}://{host}:{porta} (docs em /docs)")
    if esquema == "http" and host not in ("127.0.0.1", "localhost"):
        log.warning("Servindo em HTTP na rede — use ROBO_ALO_TLS_CERT/KEY ou um proxy HTTPS em produção.")
    uvicorn.run(app, host=host, port=porta, **ssl_kwargs)


if __name__ == "__main__":
    run()
