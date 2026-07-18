"""Servidor standalone do robô Analisador de Ligações ALO / NÃO ALO.

Sobe **apenas** os endpoints de análise de qualidade de ligações, sem depender
do scheduler, do Postgres ou das libs de ML do restante do Control Desk — ideal
para rodar o "robô" isoladamente (por padrão na porta 5501).

    python main.py alo              # porta padrão 5501
    python main.py alo 8090         # porta customizada
    python -m control_desk.alo_server
    ROBO_ALO_PORT=5501 python -m control_desk.alo_server

Sem ``ANTHROPIC_API_KEY`` (ou com ``ALO_USAR_IA=false``) roda 100% offline na
heurística. Sem Postgres, a análise ainda funciona — apenas não persiste.
"""
from __future__ import annotations

import os
from typing import Optional

from .config import CFG
from .logging_setup import get_logger

log = get_logger("alo_server")

try:
    from fastapi import FastAPI, Query
    from fastapi.middleware.cors import CORSMiddleware
    from pydantic import BaseModel

    from . import alo_store
    from .alo_analyzer import ANALISADOR
    from .alo_service import AloService

    def _backend_persistencia() -> str:
        return alo_store.backend()

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
        version="1.0.0",
        description="Avalia a qualidade da ligação entregue pela operadora ao discador.",
    )
    app.add_middleware(
        CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"]
    )

    @app.get("/", tags=["Robô"])
    def raiz():
        ia_ativa = bool(CFG.ALO_USAR_IA and CFG.ANTHROPIC_API_KEY)
        return {
            "robo": "Analisador de Ligações ALO / NÃO ALO",
            "status": "online",
            "modo": "IA (Claude)" if ia_ativa else "heurística offline",
            "modelo": CFG.ANTHROPIC_MODEL if ia_ativa else None,
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

    @app.post("/alo/analisar", tags=["ALO"])
    def analisar_ligacao(body: LigacaoIn):
        payload = body.dict()
        usar_ia = payload.pop("usar_ia", None)
        return ANALISADOR.analisar_dict(payload, usar_ia=usar_ia)

    @app.post("/alo/lote", tags=["ALO"])
    def processar_lote_payload(body: LoteIn):
        return AloService.processar_payload(
            body.chamadas, persistir=body.persistir, usar_ia=body.usar_ia
        )

    @app.get("/alo/call/{call_id}", tags=["ALO"])
    def analisar_call(call_id: str, persistir: bool = Query(True), usar_ia: Optional[bool] = Query(None)):
        return AloService.analisar_call(call_id, persistir=persistir, usar_ia=usar_ia)

    @app.post("/alo/processar", tags=["ALO"])
    def processar_alo(
        desde: Optional[str] = Query(None), limite: int = Query(200),
        persistir: bool = Query(True), usar_ia: Optional[bool] = Query(None),
    ):
        return AloService.processar_lote(desde=desde, limite=limite, persistir=persistir, usar_ia=usar_ia)

    @app.get("/alo/historico", tags=["ALO"])
    def historico_alo(
        limite: int = Query(100), classificacao: Optional[str] = Query(None),
        operadora: Optional[str] = Query(None),
    ):
        return AloService.historico(limite=limite, classificacao=classificacao, operadora=operadora)

    @app.get("/alo/estatisticas", tags=["ALO"])
    def estatisticas_alo(dias: int = Query(1)):
        return AloService.estatisticas(dias=dias)

    FASTAPI_DISPONIVEL = True

except ImportError as _e:
    log.error(f"FastAPI/uvicorn não instalados — robô ALO indisponível: {_e}")
    app = None
    FASTAPI_DISPONIVEL = False


def porta_padrao() -> int:
    return int(os.getenv("ROBO_ALO_PORT", "5501"))


def run(port: Optional[int] = None, host: str = "0.0.0.0") -> None:
    """Sobe o robô ALO. Porta: argumento > ROBO_ALO_PORT > 5501."""
    if app is None:
        raise RuntimeError(
            "FastAPI/uvicorn não instalados. Rode: pip install fastapi 'uvicorn[standard]'"
        )
    import uvicorn

    porta = port or porta_padrao()
    log.info(f"🤖 Robô Analisador ALO ouvindo em http://{host}:{porta} (docs em /docs)")
    uvicorn.run(app, host=host, port=porta)


if __name__ == "__main__":
    run()
