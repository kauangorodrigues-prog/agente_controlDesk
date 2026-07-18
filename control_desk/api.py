from __future__ import annotations

from contextlib import asynccontextmanager
from datetime import datetime, timedelta
from typing import Optional

from .config import CFG
from .db import executar_query, testar_conexao
from .logging_setup import get_logger

log = get_logger("api")

try:
    from fastapi import Depends, FastAPI, HTTPException, Query
    from fastapi.middleware.cors import CORSMiddleware
    from fastapi.responses import Response
    from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
    from jose import JWTError, jwt
    from passlib.context import CryptContext
    from prometheus_client import CONTENT_TYPE_LATEST, Counter, generate_latest
    from pydantic import BaseModel

    from .audit import AuditService
    from .discagem import DISCAGEM, treinar_async
    from .etl import ETLService
    from .forecast import ForecastService
    from .holidays import HolidayService
    from .mailing import MailingScoreService
    from .occupancy import OccupancyService
    from .pacing import PacingService
    from .scheduler import iniciar_scheduler, parar_scheduler

    pwd_ctx = CryptContext(schemes=["bcrypt"], deprecated="auto")
    oauth2 = OAuth2PasswordBearer(tokenUrl="/auth/token")
    REQ_COUNT = Counter("cd_requests_total", "Requisições", ["endpoint"])

    def _criar_token(data: dict) -> str:
        payload = {**data, "exp": datetime.utcnow() + timedelta(minutes=CFG.JWT_EXPIRE_MINUTES)}
        return jwt.encode(payload, CFG.JWT_SECRET_KEY, algorithm=CFG.JWT_ALGORITHM)

    def _verificar_token(token: str = Depends(oauth2)) -> dict:
        try:
            return jwt.decode(token, CFG.JWT_SECRET_KEY, algorithms=[CFG.JWT_ALGORITHM])
        except JWTError:
            raise HTTPException(status_code=401, detail="Token inválido ou expirado")

    def _requer_admin(payload: dict = Depends(_verificar_token)) -> dict:
        if payload.get("role") != "admin":
            raise HTTPException(status_code=403, detail="Acesso restrito a administradores")
        return payload

    class TurnoIn(BaseModel):
        falante: str = "cliente"
        texto: str = ""
        inicio_seg: Optional[float] = None

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

    class FeriadoIn(BaseModel):
        data: str
        nome: str
        tipo: str = "EMPRESA"
        uf: Optional[str] = None
        municipio: Optional[str] = None
        pausar_mailing: bool = True
        pausar_discagem: bool = True
        pacing_especial: Optional[float] = None
        observacao: Optional[str] = None

    @asynccontextmanager
    async def lifespan(app: FastAPI):
        log.info("=== Agente IA Control Desk iniciando (modo API) ===")
        iniciar_scheduler()
        yield
        parar_scheduler()

    app = FastAPI(title="Agente IA Control Desk", version="3.0.0", lifespan=lifespan)
    app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])

    # ── Auth ──────────────────────────────────────────────────────────────
    @app.post("/auth/token", tags=["Auth"])
    def login(form: OAuth2PasswordRequestForm = Depends()):
        rows = executar_query(
            "SELECT hashed_pw, role FROM api_users WHERE username = :u AND ativo = TRUE",
            {"u": form.username},
        )
        if not rows or not pwd_ctx.verify(form.password, rows[0]["hashed_pw"]):
            raise HTTPException(status_code=400, detail="Usuário ou senha incorretos")
        return {"access_token": _criar_token({"sub": form.username, "role": rows[0]["role"]}), "token_type": "bearer"}

    # ── Sistema ───────────────────────────────────────────────────────────
    @app.get("/", tags=["Sistema"])
    def health():
        return {"status": "running", "versao": "3.0.0", "banco": testar_conexao()}

    @app.get("/health", tags=["Sistema"])
    def health_detalhado():
        from .health import status_saude
        return status_saude()

    @app.get("/metrics", tags=["Sistema"])
    def metrics():
        return Response(generate_latest(), media_type=CONTENT_TYPE_LATEST)

    # ── ETL ───────────────────────────────────────────────────────────────
    @app.post("/etl/run", tags=["ETL"], dependencies=[Depends(_verificar_token)])
    def run_etl():
        return {"resultado": ETLService.run_etl()}

    # ── Ocupação ──────────────────────────────────────────────────────────
    @app.get("/ocupacao", tags=["Ocupação"], dependencies=[Depends(_verificar_token)])
    def ocupacao():
        return OccupancyService.calculate_occupancy()

    @app.get("/ocupacao/campanhas", tags=["Ocupação"], dependencies=[Depends(_verificar_token)])
    def ocupacao_campanhas():
        df = OccupancyService.por_campanha()
        return df.to_dict("records") if not df.empty else []

    # ── Pacing ────────────────────────────────────────────────────────────
    @app.post("/pacing/ajustar", tags=["Pacing"], dependencies=[Depends(_verificar_token)])
    def ajustar_pacing():
        return {"resultado": PacingService.auto_adjust_pacing()}

    @app.get("/pacing/historico", tags=["Pacing"], dependencies=[Depends(_verificar_token)])
    def historico_pacing(campanha_id: Optional[str] = Query(None), horas: int = Query(24)):
        sql = "SELECT * FROM pacing_audit_log WHERE ts >= NOW() - make_interval(hours => :h)"
        params: dict = {"h": horas}
        if campanha_id:
            sql += " AND campanha_id = :cid"
            params["cid"] = campanha_id
        sql += " ORDER BY ts DESC LIMIT 500"
        return executar_query(sql, params)

    # ── Mailing ───────────────────────────────────────────────────────────
    @app.get("/mailing/top", tags=["Mailing"], dependencies=[Depends(_verificar_token)])
    def top_mailing(n: int = Query(100), campanha_id: Optional[str] = Query(None)):
        sql = "SELECT * FROM mailing_scored"
        params: dict = {}
        if campanha_id:
            sql += " WHERE campanha_id = :cid"
            params["cid"] = campanha_id
        sql += " ORDER BY score_discagem DESC LIMIT :n"
        params["n"] = n
        return executar_query(sql, params)

    @app.post("/mailing/processar", tags=["Mailing"], dependencies=[Depends(_verificar_token)])
    def processar_mailing():
        df = MailingScoreService.calculate_score()
        return {"registros": len(df)}

    # ── Inteligência de discagem ──────────────────────────────────────────
    @app.get("/discagem/melhor-janela", tags=["Discagem"], dependencies=[Depends(_verificar_token)])
    def melhor_janela(ddd: str = Query(...), top_n: int = Query(3)):
        return DISCAGEM.melhor_janela(ddd, top_n=top_n)

    @app.post("/discagem/treinar", tags=["Discagem"], dependencies=[Depends(_verificar_token)])
    def treinar_discagem():
        treinar_async()
        return {"message": "Treino executado"}

    # ── Feriados ──────────────────────────────────────────────────────────
    @app.get("/feriados", tags=["Feriados"], dependencies=[Depends(_verificar_token)])
    def listar_feriados(ano: Optional[int] = Query(None)):
        return HolidayService.listar_feriados(ano=ano)

    @app.post("/feriados", tags=["Feriados"], dependencies=[Depends(_requer_admin)])
    def adicionar_feriado(body: FeriadoIn, payload: dict = Depends(_verificar_token)):
        from datetime import date as _date
        try:
            data_f = _date.fromisoformat(body.data)
        except ValueError:
            raise HTTPException(status_code=400, detail="Data inválida — use YYYY-MM-DD")
        ok = HolidayService.adicionar_feriado(
            data_f=data_f, nome=body.nome, tipo=body.tipo,
            uf=body.uf, municipio=body.municipio,
            pausar_mailing=body.pausar_mailing, pausar_discagem=body.pausar_discagem,
            pacing_especial=body.pacing_especial, observacao=body.observacao,
            criado_por=payload.get("sub", "API"),
        )
        if not ok:
            raise HTTPException(status_code=500, detail="Erro ao salvar feriado")
        return {"message": f"Feriado '{body.nome}' cadastrado para {body.data}"}

    @app.delete("/feriados/{feriado_id}", tags=["Feriados"], dependencies=[Depends(_requer_admin)])
    def remover_feriado(feriado_id: int):
        if not HolidayService.remover_feriado(feriado_id):
            raise HTTPException(status_code=404, detail="Feriado não encontrado")
        return {"message": f"Feriado id={feriado_id} removido"}

    @app.post("/feriados/sincronizar", tags=["Feriados"], dependencies=[Depends(_requer_admin)])
    def sincronizar_feriados(ano: Optional[int] = Query(None)):
        n = HolidayService.sincronizar_feriados_nacionais(ano=ano)
        return {"sincronizados": n}

    @app.get("/feriados/proximos", tags=["Feriados"], dependencies=[Depends(_verificar_token)])
    def proximos_feriados(dias: int = Query(30)):
        return HolidayService.proximos_feriados(dias=dias)

    # ── Forecast ──────────────────────────────────────────────────────────
    @app.get("/forecast", tags=["Forecast"], dependencies=[Depends(_verificar_token)])
    def ultimo_forecast():
        try:
            import pandas as pd
            from .db import engine
            df = pd.read_sql(
                "SELECT * FROM forecast_calls WHERE gerado_em=(SELECT MAX(gerado_em) FROM forecast_calls) ORDER BY ds",
                engine,
            )
            return df.to_dict("records")
        except Exception:
            return []

    @app.post("/forecast/gerar", tags=["Forecast"], dependencies=[Depends(_verificar_token)])
    def gerar_forecast(periodos: int = Query(24), tma_min: float = Query(5.0)):
        df = ForecastService.generate_forecast(periodos=periodos, tma_min=tma_min)
        return {"periodos": len(df)}

    # ── Auditoria ─────────────────────────────────────────────────────────
    @app.post("/auditoria/executar", tags=["Auditoria"], dependencies=[Depends(_verificar_token)])
    def executar_auditoria():
        return AuditService.run_audit()

    # ── Alertas ───────────────────────────────────────────────────────────
    @app.get("/alertas", tags=["Alertas"], dependencies=[Depends(_verificar_token)])
    def historico_alertas(nivel: Optional[str] = Query(None), limite: int = Query(50)):
        sql = "SELECT * FROM alert_log"
        params: dict = {}
        if nivel:
            sql += " WHERE nivel = :nivel"
            params["nivel"] = nivel.upper()
        sql += " ORDER BY ts DESC LIMIT :lim"
        params["lim"] = limite
        return executar_query(sql, params)

    # ── Análise de ligações (ALO / NÃO ALO) ───────────────────────────────
    @app.post("/alo/analisar", tags=["ALO"], dependencies=[Depends(_verificar_token)])
    def analisar_ligacao(body: LigacaoIn):
        from .alo_analyzer import ANALISADOR
        payload = body.dict()
        usar_ia = payload.pop("usar_ia", None)
        return ANALISADOR.analisar_dict(payload, usar_ia=usar_ia)

    class AloLoteIn(BaseModel):
        chamadas: list[dict] = []
        persistir: bool = True
        usar_ia: Optional[bool] = None

    @app.post("/alo/lote", tags=["ALO"], dependencies=[Depends(_verificar_token)])
    def processar_alo_lote(body: AloLoteIn):
        from .alo_service import AloService
        return AloService.processar_payload(body.chamadas, persistir=body.persistir, usar_ia=body.usar_ia)

    @app.get("/alo/call/{call_id}", tags=["ALO"], dependencies=[Depends(_verificar_token)])
    def analisar_call(call_id: str, persistir: bool = Query(True), usar_ia: Optional[bool] = Query(None)):
        from .alo_service import AloService
        return AloService.analisar_call(call_id, persistir=persistir, usar_ia=usar_ia)

    @app.post("/alo/processar", tags=["ALO"], dependencies=[Depends(_verificar_token)])
    def processar_alo(
        desde: Optional[str] = Query(None), limite: int = Query(200),
        persistir: bool = Query(True), usar_ia: Optional[bool] = Query(None),
    ):
        from .alo_service import AloService
        return AloService.processar_lote(desde=desde, limite=limite, persistir=persistir, usar_ia=usar_ia)

    @app.get("/alo/historico", tags=["ALO"], dependencies=[Depends(_verificar_token)])
    def historico_alo(
        limite: int = Query(100), classificacao: Optional[str] = Query(None),
        operadora: Optional[str] = Query(None),
    ):
        from .alo_service import AloService
        return AloService.historico(limite=limite, classificacao=classificacao, operadora=operadora)

    @app.get("/alo/estatisticas", tags=["ALO"], dependencies=[Depends(_verificar_token)])
    def estatisticas_alo(dias: int = Query(1)):
        from .alo_service import AloService
        return AloService.estatisticas(dias=dias)

    # ── Campanhas ─────────────────────────────────────────────────────────
    @app.get("/campanhas/config", tags=["Campanhas"], dependencies=[Depends(_verificar_token)])
    def config_campanhas():
        return executar_query("SELECT * FROM campaign_config WHERE ativo = TRUE ORDER BY campanha_nome")

    FASTAPI_DISPONIVEL = True

except ImportError as _e:
    log.warning(f"FastAPI (ou dependência) não instalado — API desativada: {_e}")
    app = None
    FASTAPI_DISPONIVEL = False
