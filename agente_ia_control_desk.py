from __future__ import annotations

# ══════════════════════════════════════════════════════════════════════
# IMPORTS GLOBAIS
# ══════════════════════════════════════════════════════════════════════

import logging
import os
import re
import smtplib
import time
import traceback
from contextlib import asynccontextmanager, contextmanager
from datetime import date, datetime, timedelta, time as dtime
from email import encoders
from email.mime.base import MIMEBase
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from logging.handlers import RotatingFileHandler
from typing import Optional

import numpy as np
import pandas as pd
import requests


# ══════════════════════════════════════════════════════════════════════
# 1. CONFIGURAÇÃO
# ══════════════════════════════════════════════════════════════════════

class Config:
    """Centraliza todas as configurações via variáveis de ambiente ou .env"""

    def __init__(self):
        # Tenta carregar .env se existir
        try:
            from dotenv import load_dotenv
            load_dotenv()
        except ImportError:
            pass

        # ── Banco de Dados ──────────────────────────────────
        self.POSTGRES_HOST     = os.getenv("POSTGRES_HOST",     "localhost")
        self.POSTGRES_PORT     = os.getenv("POSTGRES_PORT",     "5432")
        self.POSTGRES_DB       = os.getenv("POSTGRES_DB",       "control_desk")
        self.POSTGRES_USER     = os.getenv("POSTGRES_USER",     "postgres")
        self.POSTGRES_PASSWORD = os.getenv("POSTGRES_PASSWORD", "123456")

        # ── APIs ────────────────────────────────────────────
        self.DIALER_BASE_URL   = os.getenv("DIALER_BASE_URL",   "https://api.seu-discador.example.com")
        self.DIALER_TOKEN      = os.getenv("DIALER_TOKEN",      "")
        self.COLLECTOR_BASE_URL = os.getenv("COLLECTOR_BASE_URL", "https://api.seu-cobrador.example.com")
        self.COLLECTOR_TOKEN   = os.getenv("COLLECTOR_TOKEN",   "")

        # ── Alertas ─────────────────────────────────────────
        self.WEBHOOK_ALERTA   = os.getenv("WEBHOOK_ALERTA",   "")
        self.EMAIL_SMTP       = os.getenv("EMAIL_SMTP",       "")
        self.EMAIL_PORTA      = int(os.getenv("EMAIL_PORTA",  "587"))
        self.EMAIL_USER       = os.getenv("EMAIL_USER",       "")
        self.EMAIL_SENHA      = os.getenv("EMAIL_SENHA",      "")
        self.EMAIL_DESTINOS   = os.getenv("EMAIL_DESTINOS",   "")

        # ── JWT ─────────────────────────────────────────────
        self.JWT_SECRET_KEY    = os.getenv("JWT_SECRET_KEY",    "TROQUE_EM_PRODUCAO")
        self.JWT_ALGORITHM     = os.getenv("JWT_ALGORITHM",     "HS256")
        self.JWT_EXPIRE_MINUTES = int(os.getenv("JWT_EXPIRE_MINUTES", "480"))

        # ── Limites operacionais ────────────────────────────
        self.LIMITE_OCIOSIDADE_PCT     = float(os.getenv("LIMITE_OCIOSIDADE_PCT",     "15.0"))
        self.LIMITE_ABANDONO_PCT       = float(os.getenv("LIMITE_ABANDONO_PCT",       "8.0"))
        self.LIMITE_MAILING_RESTANTE   = float(os.getenv("LIMITE_MAILING_RESTANTE_PCT","5.0"))
        self.LIMITE_PAUSA_MIN          = int(os.getenv("LIMITE_PAUSA_MIN",            "20"))
        self.INTERVALO_MONITOR_SEG     = int(os.getenv("INTERVALO_MONITOR_SEG",       "120"))
        self.THROTTLE_ALERTAS_SEG      = int(os.getenv("THROTTLE_ALERTAS_SEG",        "300"))

        # ── Guardrails de Pacing ────────────────────────────
        self.PACING_HORA_INICIO_GLOBAL = os.getenv("PACING_HORA_INICIO_GLOBAL", "08:00")
        self.PACING_HORA_FIM_GLOBAL    = os.getenv("PACING_HORA_FIM_GLOBAL",    "21:00")
        self.PACING_HORA_FIM_SABADO    = os.getenv("PACING_HORA_FIM_SABADO",    "16:00")
        self.PACING_MAX_GLOBAL         = float(os.getenv("PACING_MAX_GLOBAL",   "8.0"))
        self.PACING_MIN_GLOBAL         = float(os.getenv("PACING_MIN_GLOBAL",   "1.0"))
        self.PAUSAR_EM_FERIADOS        = os.getenv("PAUSAR_EM_FERIADOS", "true").lower() == "true"

        # ── Ambiente ────────────────────────────────────────
        self.AMBIENTE  = os.getenv("AMBIENTE",  "development")
        self.LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")

        # ── CORS ────────────────────────────────────────────
        # Lista separada por vírgula; "*" libera todas as origens
        # (aceitável só em desenvolvimento).
        self.CORS_ORIGINS = os.getenv("CORS_ORIGINS", "*")

    # Valores-sentinela inseguros que NUNCA devem ir para produção.
    _DEFAULTS_INSEGUROS = {
        "JWT_SECRET_KEY": "TROQUE_EM_PRODUCAO",
        "POSTGRES_PASSWORD": "123456",
    }

    @property
    def is_producao(self) -> bool:
        return self.AMBIENTE.lower() in {"production", "producao", "prod"}

    @property
    def DATABASE_URL(self) -> str:
        return (
            f"postgresql://{self.POSTGRES_USER}:{self.POSTGRES_PASSWORD}"
            f"@{self.POSTGRES_HOST}:{self.POSTGRES_PORT}/{self.POSTGRES_DB}"
        )

    @property
    def EMAIL_DESTINOS_LIST(self) -> list:
        return [e.strip() for e in self.EMAIL_DESTINOS.split(",") if e.strip()]

    @property
    def CORS_ORIGINS_LIST(self) -> list:
        return [o.strip() for o in self.CORS_ORIGINS.split(",") if o.strip()] or ["*"]

    def problemas_seguranca(self) -> list:
        """Retorna a lista de configurações inseguras detectadas."""
        problemas = []
        if self.JWT_SECRET_KEY == self._DEFAULTS_INSEGUROS["JWT_SECRET_KEY"]:
            problemas.append("JWT_SECRET_KEY está com o valor padrão — defina um segredo forte.")
        if self.POSTGRES_PASSWORD == self._DEFAULTS_INSEGUROS["POSTGRES_PASSWORD"]:
            problemas.append("POSTGRES_PASSWORD está com o valor padrão.")
        if "*" in self.CORS_ORIGINS_LIST:
            problemas.append("CORS liberado para todas as origens (CORS_ORIGINS='*').")
        return problemas

    def validar_seguranca(self):
        """Em produção, aborta se houver configuração insegura; em dev, apenas avisa."""
        problemas = self.problemas_seguranca()
        if not problemas:
            return
        if self.is_producao:
            for p in problemas:
                log.critical(f"[Segurança] {p}")
            raise RuntimeError(
                "Configuração insegura em produção: "
                + " | ".join(problemas)
                + " Ajuste as variáveis de ambiente e suba novamente."
            )
        for p in problemas:
            log.warning(f"[Segurança] {p}")


CFG = Config()


# ══════════════════════════════════════════════════════════════════════
# 2. BANCO DE DADOS
# ══════════════════════════════════════════════════════════════════════

def _criar_engine():
    try:
        from sqlalchemy import create_engine
        from sqlalchemy.pool import QueuePool
        return create_engine(
            CFG.DATABASE_URL,
            poolclass=QueuePool,
            pool_size=5,
            max_overflow=10,
            pool_timeout=30,
            pool_recycle=1800,
            pool_pre_ping=True,
            echo=(CFG.AMBIENTE == "development"),
        )
    except Exception as e:
        print(f"[DB] Engine não criado: {e}")
        return None


engine = _criar_engine()


@contextmanager
def get_db():
    """Context manager para sessão SQLAlchemy."""
    from sqlalchemy.orm import sessionmaker
    if engine is None:
        raise RuntimeError("Banco de dados não configurado.")
    Session = sessionmaker(bind=engine)
    session = Session()
    try:
        yield session
        session.commit()
    except Exception as e:
        session.rollback()
        raise
    finally:
        session.close()


def executar_query(sql: str, params: dict = None) -> list:
    from sqlalchemy import text
    with get_db() as session:
        result = session.execute(text(sql), params or {})
        cols = result.keys()
        return [dict(zip(cols, row)) for row in result.fetchall()]


def executar_comando(sql: str, params: dict = None) -> int:
    from sqlalchemy import text
    with get_db() as session:
        result = session.execute(text(sql), params or {})
        return result.rowcount


def testar_conexao() -> bool:
    try:
        from sqlalchemy import text
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
        return True
    except Exception:
        return False


# ══════════════════════════════════════════════════════════════════════
# 3. LOGGER
# ══════════════════════════════════════════════════════════════════════

os.makedirs("logs", exist_ok=True)

_fmt = logging.Formatter(
    "%(asctime)s | %(levelname)-8s | %(name)-25s | %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
_console = logging.StreamHandler()
_console.setFormatter(_fmt)

_file = RotatingFileHandler(
    "logs/control_desk.log",
    maxBytes=10 * 1024 * 1024,
    backupCount=5,
    encoding="utf-8",
)
_file.setFormatter(_fmt)

logging.basicConfig(
    level=getattr(logging, CFG.LOG_LEVEL.upper(), logging.INFO),
    handlers=[_console, _file],
)
log = logging.getLogger("ControlDesk")


# ══════════════════════════════════════════════════════════════════════
# 4. CLIENTE DISCADOR
# ══════════════════════════════════════════════════════════════════════

class DialerClient:
    BASE    = CFG.DIALER_BASE_URL
    HEADERS = {
        "Authorization": f"Bearer {CFG.DIALER_TOKEN}",
        "Content-Type": "application/json",
    }
    TIMEOUT = 15

    @classmethod
    def _get(cls, endpoint: str, params: dict = None) -> dict:
        for tentativa in range(1, 4):
            try:
                r = requests.get(
                    f"{cls.BASE}{endpoint}",
                    headers=cls.HEADERS,
                    params=params,
                    timeout=cls.TIMEOUT,
                )
                r.raise_for_status()
                return r.json()
            except (requests.Timeout, requests.ConnectionError) as e:
                log.warning(f"[Dialer] Tentativa {tentativa}/3 falhou em {endpoint}: {e}")
                time.sleep(2 ** tentativa)
            except Exception as e:
                log.error(f"[Dialer] Erro em {endpoint}: {e}")
                return {}
        return {}

    @classmethod
    def _put(cls, endpoint: str, payload: dict) -> dict:
        for tentativa in range(1, 4):
            try:
                r = requests.put(
                    f"{cls.BASE}{endpoint}",
                    headers=cls.HEADERS,
                    json=payload,
                    timeout=cls.TIMEOUT,
                )
                r.raise_for_status()
                return r.json()
            except (requests.Timeout, requests.ConnectionError) as e:
                log.warning(f"[Dialer] PUT tentativa {tentativa}/3 falhou: {e}")
                time.sleep(2 ** tentativa)
            except Exception as e:
                log.error(f"[Dialer] Erro PUT {endpoint}: {e}")
                return {}
        return {}

    @classmethod
    def get_agents(cls) -> list:
        d = cls._get("/agents")
        return d.get("agents", d if isinstance(d, list) else [])

    @classmethod
    def get_calls(cls, data_inicio: str = None) -> list:
        params = {"from": data_inicio} if data_inicio else {}
        d = cls._get("/calls/history", params=params)
        return d.get("calls", d if isinstance(d, list) else [])

    @classmethod
    def get_campaign_snapshot(cls) -> list:
        d = cls._get("/campaigns/snapshot")
        return d.get("data", d if isinstance(d, list) else [])

    @classmethod
    def get_mailing_status(cls) -> list:
        d = cls._get("/mailing/status")
        return d.get("mailings", d if isinstance(d, list) else [])

    @classmethod
    def update_pacing(cls, campaign_id: str, pacing: float) -> dict:
        result = cls._put(f"/campaigns/{campaign_id}/pacing", {"pacing": round(pacing, 1)})
        log.info(f"[Dialer] Pacing: campanha={campaign_id} pacing={pacing}")
        return result

    @classmethod
    def pause_campaign(cls, campaign_id: str, motivo: str = "") -> dict:
        result = cls._put(f"/campaigns/{campaign_id}/pause", {"reason": motivo})
        log.info(f"[Dialer] Campanha pausada: {campaign_id} — {motivo}")
        return result

    @classmethod
    def resume_campaign(cls, campaign_id: str) -> dict:
        result = cls._put(f"/campaigns/{campaign_id}/resume", {})
        log.info(f"[Dialer] Campanha retomada: {campaign_id}")
        return result


# ══════════════════════════════════════════════════════════════════════
# 5. CLIENTE COBRADOR / CRM
# ══════════════════════════════════════════════════════════════════════

class CollectorClient:
    BASE    = CFG.COLLECTOR_BASE_URL
    HEADERS = {
        "Authorization": f"Bearer {CFG.COLLECTOR_TOKEN}",
        "Content-Type": "application/json",
    }
    TIMEOUT = 15

    @classmethod
    def _get(cls, endpoint: str, params: dict = None) -> dict:
        for tentativa in range(1, 4):
            try:
                r = requests.get(
                    f"{cls.BASE}{endpoint}",
                    headers=cls.HEADERS,
                    params=params,
                    timeout=cls.TIMEOUT,
                )
                r.raise_for_status()
                return r.json()
            except (requests.Timeout, requests.ConnectionError) as e:
                log.warning(f"[Collector] Tentativa {tentativa}/3 falhou: {e}")
                time.sleep(2 ** tentativa)
            except Exception as e:
                log.error(f"[Collector] Erro {endpoint}: {e}")
                return {}
        return {}

    @classmethod
    def get_customers(cls, campanha_id: str = None) -> list:
        params = {"campaign_id": campanha_id} if campanha_id else {}
        d = cls._get("/customers", params=params)
        return d.get("customers", d if isinstance(d, list) else [])

    @classmethod
    def get_promises(cls, data: str = None) -> list:
        params = {"date": data} if data else {}
        d = cls._get("/promises", params=params)
        return d.get("promises", d if isinstance(d, list) else [])

    @classmethod
    def get_portfolios(cls) -> list:
        d = cls._get("/portfolios/active")
        return d.get("portfolios", d if isinstance(d, list) else [])


# ══════════════════════════════════════════════════════════════════════
# 6. ALERTAS VIA WEBHOOK
# ══════════════════════════════════════════════════════════════════════

_throttle_cache: dict[str, datetime] = {}
ICONES_ALERTA = {"INFO": "ℹ️", "ATENCAO": "⚠️", "CRITICO": "🔴"}


def _registrar_alerta_banco(chave: str, nivel: str, mensagem: str, enviado: bool):
    try:
        executar_comando(
            "INSERT INTO alert_log (chave, nivel, mensagem, canal, enviado, ts) "
            "VALUES (:chave, :nivel, :mensagem, 'webhook', :enviado, NOW())",
            {"chave": chave, "nivel": nivel, "mensagem": mensagem, "enviado": enviado},
        )
    except Exception as e:
        log.debug(f"Falha ao registrar alerta no banco: {e}")


def pode_enviar_alerta(chave: str, throttle_seg: int = None) -> bool:
    throttle = throttle_seg or CFG.THROTTLE_ALERTAS_SEG
    agora = datetime.utcnow()
    ultimo = _throttle_cache.get(chave)
    if ultimo and (agora - ultimo).total_seconds() < throttle:
        return False
    _throttle_cache[chave] = agora
    return True


def send_webhook_alert(
    mensagem: str,
    nivel: str = "INFO",
    chave: str = "geral",
    throttle_seg: int = None,
    forcar: bool = False,
) -> bool:
    if not CFG.WEBHOOK_ALERTA:
        log.warning("WEBHOOK_ALERTA não configurado.")
        return False

    if not forcar and not pode_enviar_alerta(chave, throttle_seg):
        return False

    icone = ICONES_ALERTA.get(nivel.upper(), "📢")
    payload = {"text": f"{icone} **[{nivel.upper()}]** {mensagem}"}

    for tentativa in range(1, 4):
        try:
            r = requests.post(CFG.WEBHOOK_ALERTA, json=payload, timeout=10)
            r.raise_for_status()
            log.info(f"[Webhook] Enviado: chave={chave} nivel={nivel}")
            _registrar_alerta_banco(chave, nivel, mensagem, True)
            return True
        except requests.Timeout:
            log.warning(f"[Webhook] Timeout na tentativa {tentativa}/3")
        except Exception as e:
            log.error(f"[Webhook] Erro tentativa {tentativa}/3: {e}")
            break

    _registrar_alerta_banco(chave, nivel, mensagem, False)
    return False


# ══════════════════════════════════════════════════════════════════════
# 7. ETL SERVICE
# ══════════════════════════════════════════════════════════════════════

class ETLService:

    @staticmethod
    def _salvar(df: pd.DataFrame, tabela: str, schema_min: set = None) -> int:
        if df is None or df.empty:
            log.warning(f"[ETL] DataFrame vazio — {tabela} não atualizada")
            return 0
        if schema_min:
            faltando = schema_min - set(df.columns)
            if faltando:
                log.error(f"[ETL] Schema inválido para '{tabela}': {faltando}")
                return 0
        df = df.copy()
        df["etl_ts"] = datetime.utcnow()
        try:
            df.to_sql(tabela, engine, if_exists="append", index=False, method="multi", chunksize=500)
            log.info(f"[ETL] {len(df)} linha(s) → {tabela}")
            return len(df)
        except Exception as e:
            log.error(f"[ETL] Erro ao salvar '{tabela}': {e}")
            return 0

    @staticmethod
    def run_etl() -> dict:
        log.info("=== ETL Iniciado ===")
        inicio = datetime.utcnow()
        resultado = {}

        # Agentes
        try:
            dados = DialerClient.get_agents()
            df = pd.DataFrame(dados)
            if not df.empty and "status" in df.columns:
                df["status"] = df["status"].str.upper().str.strip()
            resultado["agentes"] = ETLService._salvar(df, "agents", {"agente_id", "nome", "status"})
        except Exception:
            log.error(f"[ETL] Falha agentes:\n{traceback.format_exc()}")
            resultado["agentes"] = 0

        # Chamadas
        try:
            ontem = (date.today() - timedelta(days=1)).isoformat()
            dados = DialerClient.get_calls(data_inicio=ontem)
            df = pd.DataFrame(dados)
            if not df.empty and "telefone" in df.columns:
                df["ddd"] = df["telefone"].astype(str).str.replace(r"\D", "", regex=True).str[:2]
            resultado["chamadas"] = ETLService._salvar(df, "calls", {"call_id", "status"})
        except Exception:
            log.error(f"[ETL] Falha chamadas:\n{traceback.format_exc()}")
            resultado["chamadas"] = 0

        # Snapshot campanhas
        try:
            dados = DialerClient.get_campaign_snapshot()
            resultado["campanhas"] = ETLService._salvar(pd.DataFrame(dados), "campaign_snapshot")
        except Exception:
            log.error(f"[ETL] Falha snapshot:\n{traceback.format_exc()}")
            resultado["campanhas"] = 0

        # Mailing status
        try:
            dados = DialerClient.get_mailing_status()
            resultado["mailing"] = ETLService._salvar(pd.DataFrame(dados), "mailing_status")
        except Exception:
            log.error(f"[ETL] Falha mailing:\n{traceback.format_exc()}")
            resultado["mailing"] = 0

        # Clientes CRM / Cobrador
        try:
            dados = CollectorClient.get_customers()
            df = pd.DataFrame(dados)
            if not df.empty and "telefone" in df.columns:
                df["telefone_limpo"] = df["telefone"].astype(str).str.replace(r"\D", "", regex=True)
                df["ddd"] = df["telefone_limpo"].str[:2]
            resultado["clientes"] = ETLService._salvar(df, "customers", {"cpf", "telefone"})
        except Exception:
            log.error(f"[ETL] Falha clientes:\n{traceback.format_exc()}")
            resultado["clientes"] = 0

        # Promessas
        try:
            dados = CollectorClient.get_promises(data=date.today().isoformat())
            resultado["promessas"] = ETLService._salvar(pd.DataFrame(dados), "collector_promessas")
        except Exception:
            log.error(f"[ETL] Falha promessas:\n{traceback.format_exc()}")
            resultado["promessas"] = 0

        dur = (datetime.utcnow() - inicio).total_seconds()
        log.info(f"=== ETL Concluído em {dur:.1f}s | {sum(resultado.values())} linhas ===")
        return resultado


# ══════════════════════════════════════════════════════════════════════
# 8. OCCUPANCY SERVICE
# ══════════════════════════════════════════════════════════════════════

STATUS_OCIOSO  = {"available", "idle", "livre", "free", "disponivel"}
STATUS_PAUSA   = {"paused", "pause", "break", "pausa"}
STATUS_LIGANDO = {"on_call", "oncall", "dialing", "talking", "em_ligacao"}


class OccupancyService:

    @staticmethod
    def _ler_agentes() -> pd.DataFrame:
        df = pd.read_sql(
            "SELECT * FROM agents WHERE captured_at >= NOW() - INTERVAL '6 minutes'", engine
        )
        if not df.empty:
            df["status_norm"] = df["status"].astype(str).str.lower().str.strip()
        return df

    @staticmethod
    def calculate_occupancy() -> dict:
        df = OccupancyService._ler_agentes()

        if df.empty:
            log.warning("[Ocupação] Sem agentes nos últimos 6 min.")
            return {
                "total": 0, "ociosos": 0, "em_pausa": 0, "em_ligacao": 0,
                "ocupacao_pct": 0.0, "ociosidade_pct": 0.0,
                "agentes_pausa_longa": [], "erro": "Sem agentes logados",
            }

        total      = len(df)
        ociosos    = int(df["status_norm"].isin(STATUS_OCIOSO).sum())
        em_pausa   = int(df["status_norm"].isin(STATUS_PAUSA).sum())
        em_ligacao = int(df["status_norm"].isin(STATUS_LIGANDO).sum())
        ocupacao_pct   = round(((total - ociosos) / total) * 100, 2)
        ociosidade_pct = round((ociosos / total) * 100, 2)

        agentes_pausa_longa = []
        if "pausa_inicio" in df.columns:
            agora = datetime.utcnow()
            df_p  = df[df["status_norm"].isin(STATUS_PAUSA)].copy()
            df_p["pausa_inicio"] = pd.to_datetime(df_p["pausa_inicio"], errors="coerce")
            df_p = df_p.dropna(subset=["pausa_inicio"])
            df_p["min_pausa"] = (agora - df_p["pausa_inicio"].dt.tz_localize(None)).dt.total_seconds() / 60
            longos = df_p[df_p["min_pausa"] > CFG.LIMITE_PAUSA_MIN]
            agentes_pausa_longa = [
                {"nome": r.get("nome", "?"), "min_pausa": round(r["min_pausa"])}
                for _, r in longos.iterrows()
            ]

        metricas = {
            "total": total, "ociosos": ociosos, "em_pausa": em_pausa,
            "em_ligacao": em_ligacao, "ocupacao_pct": ocupacao_pct,
            "ociosidade_pct": ociosidade_pct,
            "agentes_pausa_longa": agentes_pausa_longa,
            "ts": datetime.utcnow().isoformat(),
        }

        # Alertas
        if ociosidade_pct > CFG.LIMITE_OCIOSIDADE_PCT:
            send_webhook_alert(
                f"Ociosidade em *{ociosidade_pct:.1f}%* (limite {CFG.LIMITE_OCIOSIDADE_PCT}%)\n"
                f"Ociosos: {ociosos}/{total}",
                nivel="ATENCAO", chave="ociosidade_alta",
            )

        if agentes_pausa_longa:
            nomes = ", ".join(a["nome"] for a in agentes_pausa_longa[:5])
            send_webhook_alert(
                f"Agentes em pausa >  {CFG.LIMITE_PAUSA_MIN} min: {nomes}",
                nivel="ATENCAO", chave="pausa_longa",
            )

        return metricas

    @staticmethod
    def por_campanha() -> pd.DataFrame:
        df = OccupancyService._ler_agentes()
        if df.empty or "campanha" not in df.columns:
            return pd.DataFrame()
        g = (
            df.groupby("campanha")
            .agg(
                total=("agente_id", "count"),
                ociosos=("status_norm", lambda x: x.isin(STATUS_OCIOSO).sum()),
                em_pausa=("status_norm", lambda x: x.isin(STATUS_PAUSA).sum()),
                em_ligacao=("status_norm", lambda x: x.isin(STATUS_LIGANDO).sum()),
            )
            .reset_index()
        )
        g["ociosidade_pct"] = (g["ociosos"] / g["total"] * 100).round(1)
        g["ocupacao_pct"]   = ((g["total"] - g["ociosos"]) / g["total"] * 100).round(1)
        return g


# ══════════════════════════════════════════════════════════════════════
# 9. HOLIDAY SERVICE
# ══════════════════════════════════════════════════════════════════════

def _str_para_time(s: str) -> dtime:
    try:
        p = str(s).split(":")
        return dtime(int(p[0]), int(p[1]))
    except Exception:
        return dtime(8, 0)


class HolidayService:

    @staticmethod
    def _feriados_banco(data_alvo: date = None) -> pd.DataFrame:
        data_alvo = data_alvo or date.today()
        try:
            rows = executar_query(
                "SELECT * FROM feriados WHERE data = :d ORDER BY tipo",
                {"d": data_alvo.isoformat()},
            )
            return pd.DataFrame(rows)
        except Exception:
            return pd.DataFrame()

    @staticmethod
    def e_feriado(data_alvo: date = None, uf: str = None) -> tuple:
        data_alvo = data_alvo or date.today()
        if not CFG.PAUSAR_EM_FERIADOS:
            return False, ""
        df = HolidayService._feriados_banco(data_alvo)
        if df.empty:
            return False, ""
        for _, row in df.iterrows():
            tipo = row.get("tipo", "NACIONAL")
            if not row.get("pausar_discagem", True):
                continue
            if tipo == "NACIONAL":
                return True, row["nome"]
            if tipo == "ESTADUAL" and uf and str(row.get("uf", "")).upper() == uf.upper():
                return True, row["nome"]
            if tipo == "EMPRESA":
                return True, row["nome"]
        return False, ""

    @staticmethod
    def pausar_mailing_hoje(data_alvo: date = None) -> tuple:
        data_alvo = data_alvo or date.today()
        df = HolidayService._feriados_banco(data_alvo)
        if df.empty:
            return False, ""
        for _, row in df.iterrows():
            if row.get("pausar_mailing", True):
                return True, row["nome"]
        return False, ""

    @staticmethod
    def dentro_do_horario(campanha_id: str = None, agora: datetime = None) -> tuple:
        agora = agora or datetime.now()
        hora_atual  = agora.time()
        dia_semana  = agora.weekday()

        config = None
        if campanha_id:
            try:
                rows = executar_query(
                    "SELECT * FROM campaign_config WHERE campanha_id = :id AND ativo = TRUE",
                    {"id": campanha_id},
                )
                config = rows[0] if rows else None
            except Exception:
                pass

        if config:
            hora_ini    = _str_para_time(str(config.get("hora_inicio", CFG.PACING_HORA_INICIO_GLOBAL)))
            hora_fim_s  = _str_para_time(str(config.get("hora_fim",    CFG.PACING_HORA_FIM_GLOBAL)))
            hora_fim_sa = _str_para_time(str(config.get("hora_fim_sabado", CFG.PACING_HORA_FIM_SABADO)))
            permite_dom = config.get("permitir_domingo", False)
        else:
            hora_ini    = _str_para_time(CFG.PACING_HORA_INICIO_GLOBAL)
            hora_fim_s  = _str_para_time(CFG.PACING_HORA_FIM_GLOBAL)
            hora_fim_sa = _str_para_time(CFG.PACING_HORA_FIM_SABADO)
            permite_dom = False

        if dia_semana == 6 and not permite_dom:
            return False, f"Discagem bloqueada aos domingos"

        hora_fim = hora_fim_sa if dia_semana == 5 else hora_fim_s

        if hora_atual < hora_ini:
            return False, f"Antes do horário permitido (início: {hora_ini.strftime('%H:%M')})"
        if hora_atual >= hora_fim:
            return False, f"Após o horário permitido (fim: {hora_fim.strftime('%H:%M')})"

        return True, ""

    @staticmethod
    def pacing_permitido(campanha_id: str = None, uf: str = None, agora: datetime = None) -> tuple:
        agora = agora or datetime.now()
        e_fer, nome = HolidayService.e_feriado(agora.date(), uf=uf)
        if e_fer:
            return False, f"Feriado: {nome}"
        return HolidayService.dentro_do_horario(campanha_id, agora)

    @staticmethod
    def listar_feriados(ano: int = None) -> list:
        ano = ano or date.today().year
        try:
            return executar_query(
                "SELECT * FROM feriados WHERE EXTRACT(YEAR FROM data) = :ano ORDER BY data",
                {"ano": ano},
            )
        except Exception:
            return []

    @staticmethod
    def adicionar_feriado(
        data_f: date, nome: str, tipo: str = "EMPRESA",
        uf: str = None, municipio: str = None,
        pausar_mailing: bool = True, pausar_discagem: bool = True,
        pacing_especial: float = None, observacao: str = None,
        criado_por: str = "USUARIO",
    ) -> bool:
        try:
            executar_comando(
                """
                INSERT INTO feriados
                    (data, nome, tipo, uf, municipio, pausar_mailing,
                     pausar_discagem, pacing_especial, observacao, criado_por)
                VALUES (:data, :nome, :tipo, :uf, :municipio, :pm,
                        :pd, :pe, :obs, :criado)
                ON CONFLICT (data, tipo, COALESCE(uf, ''), COALESCE(municipio, '')) DO UPDATE
                    SET nome = EXCLUDED.nome,
                        pausar_mailing  = EXCLUDED.pausar_mailing,
                        pausar_discagem = EXCLUDED.pausar_discagem,
                        pacing_especial = EXCLUDED.pacing_especial,
                        observacao      = EXCLUDED.observacao
                """,
                {
                    "data": data_f.isoformat(), "nome": nome, "tipo": tipo.upper(),
                    "uf": uf, "municipio": municipio,
                    "pm": pausar_mailing, "pd": pausar_discagem,
                    "pe": pacing_especial, "obs": observacao, "criado": criado_por,
                },
            )
            log.info(f"[Feriado] Adicionado: {data_f} — {nome}")
            return True
        except Exception as e:
            log.error(f"[Feriado] Erro: {e}")
            return False

    @staticmethod
    def remover_feriado(feriado_id: int) -> bool:
        try:
            n = executar_comando("DELETE FROM feriados WHERE id = :id", {"id": feriado_id})
            return n > 0
        except Exception:
            return False

    @staticmethod
    def proximos_feriados(dias: int = 30) -> list:
        try:
            fim = date.today() + timedelta(days=dias)
            return executar_query(
                "SELECT * FROM feriados WHERE data BETWEEN :i AND :f ORDER BY data",
                {"i": date.today().isoformat(), "f": fim.isoformat()},
            )
        except Exception:
            return []

    @staticmethod
    def sincronizar_feriados_nacionais(ano: int = None) -> int:
        ano = ano or date.today().year
        inseridos = 0
        try:
            import holidays as hol_lib
            br = hol_lib.Brazil(years=ano)
            for data_f, nome in br.items():
                if HolidayService.adicionar_feriado(data_f, nome, "NACIONAL", criado_por="SISTEMA_AUTO"):
                    inseridos += 1
            log.info(f"[Feriado] {inseridos} feriados nacionais sincronizados para {ano}")
        except ImportError:
            log.warning("[Feriado] Biblioteca 'holidays' não instalada.")
        return inseridos


# ══════════════════════════════════════════════════════════════════════
# 10. PACING SERVICE
# ══════════════════════════════════════════════════════════════════════

class PacingService:

    @staticmethod
    def _configs() -> dict:
        try:
            rows = executar_query("SELECT * FROM campaign_config WHERE ativo = TRUE")
            return {r["campanha_id"]: r for r in rows}
        except Exception:
            return {}

    @staticmethod
    def _campanhas_ativas() -> list:
        try:
            return executar_query(
                """
                SELECT DISTINCT ON (campanha_id)
                    campanha_id, campanha, pacing_atual,
                    mailing_restante_pct, ocupacao_pct, ociosidade_pct, abandono_pct
                FROM campaign_snapshot
                WHERE captured_at >= NOW() - INTERVAL '10 minutes'
                  AND status = 'ACTIVE'
                ORDER BY campanha_id, captured_at DESC
                """
            )
        except Exception:
            return []

    @staticmethod
    def _calcular_pacing(
        ocupacao_pct: float, abandono_pct: float,
        pacing_min: float, pacing_max: float,
    ) -> tuple:
        if abandono_pct > CFG.LIMITE_ABANDONO_PCT:
            novo = pacing_min + (pacing_max - pacing_min) * 0.3
            return round(min(max(novo, pacing_min), pacing_max), 1), "abandono_alto"
        ociosidade = 100 - ocupacao_pct
        fator = ociosidade / 100
        novo = pacing_min + (pacing_max - pacing_min) * fator
        return round(min(max(novo, pacing_min), pacing_max), 1), "ajuste_proporcional"

    @staticmethod
    def _log_auditoria(
        cid: str, cnome: str, pant: float, pnovo: float,
        motivo: str, ocup: float, bloqueado: bool = False, mbloq: str = "",
    ):
        try:
            executar_comando(
                """
                INSERT INTO pacing_audit_log
                    (campanha_id, campanha_nome, pacing_anterior, pacing_novo,
                     motivo, ocupacao_pct, bloqueado, motivo_bloqueio, ts)
                VALUES (:cid, :cnome, :pant, :pnovo, :motivo, :ocup, :bloq, :mbloq, NOW())
                """,
                {
                    "cid": cid, "cnome": cnome, "pant": pant, "pnovo": pnovo,
                    "motivo": motivo, "ocup": ocup, "bloq": bloqueado, "mbloq": mbloq,
                },
            )
        except Exception as e:
            log.debug(f"[Pacing] Falha ao registrar auditoria: {e}")

    @staticmethod
    def auto_adjust_pacing() -> dict:
        configs   = PacingService._configs()
        campanhas = PacingService._campanhas_ativas()
        agora     = datetime.now()
        resultado = {}

        for camp in campanhas:
            cid   = camp["campanha_id"]
            cnome = camp.get("campanha", cid)
            cfg   = configs.get(cid, {})
            uf    = cfg.get("uf_restricao")

            pacing_min  = float(cfg.get("pacing_min",  CFG.PACING_MIN_GLOBAL))
            pacing_max  = float(cfg.get("pacing_max",  CFG.PACING_MAX_GLOBAL))
            pacing_at   = float(camp.get("pacing_atual", 2.0))
            ocup_pct    = float(camp.get("ocupacao_pct", 80.0))
            aband_pct   = float(camp.get("abandono_pct", 0.0))

            # ── GUARDRAIL: Feriado / Horário ──────────────
            permitido, motivo_bloq = HolidayService.pacing_permitido(cid, uf=uf, agora=agora)
            if not permitido:
                log.info(f"[Pacing] {cnome} BLOQUEADO: {motivo_bloq}")
                PacingService._log_auditoria(cid, cnome, pacing_at, 0,
                    "bloqueado_guardrail", ocup_pct, True, motivo_bloq)
                resultado[cid] = {"status": "bloqueado", "motivo": motivo_bloq}
                continue

            # ── GUARDRAIL: Pausa total em feriado ─────────
            pausar, nome_fer = HolidayService.pausar_mailing_hoje()
            if pausar and cfg.get("pausar_feriados", True):
                try:
                    DialerClient.pause_campaign(cid, f"Feriado: {nome_fer}")
                except Exception:
                    pass
                send_webhook_alert(
                    f"Campanha *{cnome}* pausada — {nome_fer}",
                    nivel="INFO", chave=f"pausa_feriado_{cid}", throttle_seg=3600,
                )
                PacingService._log_auditoria(cid, cnome, pacing_at, 0,
                    "pausa_feriado", ocup_pct, True, f"Feriado: {nome_fer}")
                resultado[cid] = {"status": "pausado", "motivo": f"Feriado: {nome_fer}"}
                continue

            # ── Cálculo ───────────────────────────────────
            novo_pacing, motivo_calc = PacingService._calcular_pacing(
                ocup_pct, aband_pct, pacing_min, pacing_max,
            )

            if abs(novo_pacing - pacing_at) < 0.5:
                resultado[cid] = {"status": "sem_alteracao", "pacing": pacing_at}
                continue

            try:
                DialerClient.update_pacing(cid, novo_pacing)
            except Exception as e:
                log.error(f"[Pacing] API falhou {cid}: {e}")
                resultado[cid] = {"status": "erro_api"}
                continue

            PacingService._log_auditoria(cid, cnome, pacing_at, novo_pacing, motivo_calc, ocup_pct)
            dir_seta = "↑" if novo_pacing > pacing_at else "↓"
            log.info(f"[Pacing] {cnome}: {pacing_at} → {novo_pacing} {dir_seta}")
            resultado[cid] = {
                "status": "ajustado",
                "pacing_anterior": pacing_at,
                "pacing_novo": novo_pacing,
            }

        return resultado

    @staticmethod
    def retomar_pos_feriado():
        e_fer, _ = HolidayService.e_feriado()
        if e_fer:
            return
        try:
            rows = executar_query(
                """
                SELECT DISTINCT campanha_id, campanha_nome
                FROM pacing_audit_log
                WHERE motivo_bloqueio LIKE 'Feriado%'
                  AND DATE(ts) = CURRENT_DATE - 1
                """
            )
            for r in rows:
                DialerClient.resume_campaign(r["campanha_id"])
                log.info(f"[Pacing] Retomada pós-feriado: {r['campanha_nome']}")
        except Exception as e:
            log.error(f"[Pacing] Erro retomada: {e}")


# ══════════════════════════════════════════════════════════════════════
# 11. MAILING SCORE SERVICE
# ══════════════════════════════════════════════════════════════════════

DDDS_VALIDOS = {
    str(d) for d in
    list(range(11, 20)) + list(range(21, 30)) +
    list(range(31, 40)) + list(range(41, 50)) +
    list(range(51, 70)) + list(range(71, 99))
}

DDD_SCORE_MAP = {
    "11": 10, "21": 9, "31": 8, "41": 8, "51": 7,
    "71": 7,  "61": 6, "85": 6, "81": 6,
}


class MailingScoreService:

    @staticmethod
    def validar_cpf(cpf: str) -> bool:
        cpf = re.sub(r"\D", "", str(cpf or ""))
        if len(cpf) != 11 or len(set(cpf)) == 1:
            return False
        for i in range(2):
            soma = sum(int(cpf[j]) * (10 + i - j) for j in range(9 + i))
            if (soma * 10 % 11) % 10 != int(cpf[9 + i]):
                return False
        return True

    @staticmethod
    def validar_telefone(tel: str) -> Optional[str]:
        digits = re.sub(r"\D", "", str(tel or ""))
        if len(digits) not in (10, 11):
            return None
        if digits[:2] not in DDDS_VALIDOS:
            return None
        return digits

    @staticmethod
    def calcular_score(row: pd.Series) -> float:
        if not {"cpf", "telefone"}.issubset(set(row.index)):
            return 0.0
        score = 0.0
        score += min(float(row.get("previous_cpc", 0) or 0) * 30, 30)
        dias = float(row.get("days_delay", 30) or 30)
        score += max(0.0, 20 - dias * 0.4)
        faixa = int(row.get("faixa_atraso_dias", 0) or 0)
        score += 15 if 30 <= faixa <= 90 else 8 if faixa < 30 else 4
        h = datetime.now().hour
        h_ini = int(row.get("melhor_hora_inicio", 8) or 8)
        h_fim = int(row.get("melhor_hora_fim", 20) or 20)
        if h_ini <= h <= h_fim:
            score += 15
        score += DDD_SCORE_MAP.get(str(row.get("ddd", ""))[:2], 5)
        if row.get("promessa_quebrada"):
            score -= 10
        return round(max(0.0, min(score, 100.0)), 2)

    @staticmethod
    def calculate_score(caminho_csv: str = None) -> pd.DataFrame:
        if caminho_csv and os.path.exists(caminho_csv):
            df = pd.read_csv(caminho_csv, dtype=str)
        else:
            df = pd.read_sql("SELECT * FROM customers WHERE ativo = TRUE", engine)

        if df.empty:
            return df

        if not {"cpf", "telefone"}.issubset(set(df.columns)):
            log.error("[Mailing] Colunas cpf/telefone ausentes.")
            return pd.DataFrame()

        df = df[df["cpf"].apply(MailingScoreService.validar_cpf)].copy()
        df["telefone_limpo"] = df["telefone"].apply(MailingScoreService.validar_telefone)
        df = df[df["telefone_limpo"].notna()].copy()
        df["ddd"] = df["telefone_limpo"].str[:2]

        if "captured_at" in df.columns:
            df = df.sort_values("captured_at", ascending=False)
        df = df.drop_duplicates(subset=["cpf"]).copy()

        for col in ["days_delay", "previous_cpc", "phone_score", "faixa_atraso_dias",
                    "melhor_hora_inicio", "melhor_hora_fim"]:
            if col in df.columns:
                df[col] = pd.to_numeric(df[col], errors="coerce").fillna(0)

        if "promessa_quebrada" in df.columns:
            df["promessa_quebrada"] = df["promessa_quebrada"].astype(str).isin(
                ["1", "True", "true", "t", "yes"]
            )

        df["score_discagem"] = df.apply(MailingScoreService.calcular_score, axis=1)
        df = df.sort_values("score_discagem", ascending=False).reset_index(drop=True)

        try:
            df["scored_at"] = datetime.utcnow()
            df.to_sql("mailing_scored", engine, if_exists="replace", index=False)
        except Exception as e:
            log.error(f"[Mailing] Erro ao salvar: {e}")

        os.makedirs("data/output", exist_ok=True)
        saida = f"data/output/mailing_priorizado_{date.today()}.csv"
        df.to_csv(saida, index=False)
        log.info(f"[Mailing] {len(df)} registros → {saida}")
        return df


# ══════════════════════════════════════════════════════════════════════
# 12. FORECAST SERVICE
# ══════════════════════════════════════════════════════════════════════

class ForecastService:

    @staticmethod
    def _serie() -> pd.DataFrame:
        df = pd.read_sql(
            "SELECT DATE_TRUNC('hour', iniciada_em) AS ds, COUNT(*) AS y "
            "FROM calls WHERE iniciada_em >= NOW() - INTERVAL '180 days' "
            "GROUP BY 1 ORDER BY 1",
            engine,
        )
        df["ds"] = pd.to_datetime(df["ds"])
        return df

    @staticmethod
    def _fallback(df: pd.DataFrame, periodos: int) -> pd.DataFrame:
        df = df.copy()
        df["dow"]  = df["ds"].dt.dayofweek
        df["hora"] = df["ds"].dt.hour
        medias = df.groupby(["dow", "hora"])["y"].mean()
        ultima = df["ds"].max()
        rows = []
        for i in range(1, periodos + 1):
            prox = ultima + timedelta(hours=i)
            m = medias.get((prox.dayofweek, prox.hour), df["y"].mean())
            rows.append({
                "ds": prox,
                "yhat": round(max(m, 0)),
                "yhat_lower": round(max(m * 0.80, 0)),
                "yhat_upper": round(m * 1.20),
            })
        return pd.DataFrame(rows)

    @staticmethod
    def generate_forecast(periodos: int = 24, tma_min: float = 5.0) -> pd.DataFrame:
        log.info("[Forecast] Gerando previsão...")
        df = ForecastService._serie()
        if df.empty or len(df) < 48:
            log.warning("[Forecast] Histórico insuficiente.")
            return pd.DataFrame()

        try:
            from prophet import Prophet
            m = Prophet(weekly_seasonality=True, daily_seasonality=True, yearly_seasonality=False)
            m.fit(df[["ds", "y"]])
            futuro = m.make_future_dataframe(periods=periodos, freq="H")
            fc = m.predict(futuro)
            fc = fc[["ds", "yhat", "yhat_lower", "yhat_upper"]].tail(periodos)
            log.info("[Forecast] Método: Prophet")
        except (ImportError, Exception) as e:
            log.warning(f"[Forecast] Prophet indisponível ({e}) — usando fallback.")
            fc = ForecastService._fallback(df, periodos)

        fc["agentes_necessarios"] = (fc["yhat"] * (tma_min / 60)).apply(np.ceil).clip(lower=0).astype(int)
        fc["gerado_em"] = datetime.utcnow()

        try:
            fc.to_sql("forecast_calls", engine, if_exists="append", index=False)
        except Exception as e:
            log.error(f"[Forecast] Erro ao salvar: {e}")

        return fc


# ══════════════════════════════════════════════════════════════════════
# 13. AUDIT SERVICE
# ══════════════════════════════════════════════════════════════════════

class AuditService:

    @staticmethod
    def run_audit() -> dict:
        log.info("=== Auditoria Operacional ===")
        relatorio = {}
        problemas = []

        # Agentes improdutivos
        try:
            df = pd.read_sql(
                """
                SELECT a.nome, a.campanha,
                       ROUND(EXTRACT(EPOCH FROM (NOW()-a.login_em))/60) AS min_logado,
                       COALESCE(l.ligacoes,0) AS ligacoes_hoje
                FROM agents a
                LEFT JOIN (
                    SELECT agente_id, COUNT(*) AS ligacoes
                    FROM calls WHERE DATE(iniciada_em) = CURRENT_DATE GROUP BY agente_id
                ) l ON a.agente_id = l.agente_id
                WHERE a.captured_at >= NOW() - INTERVAL '5 minutes'
                  AND LOWER(a.status) NOT IN ('paused','offline')
                  AND EXTRACT(EPOCH FROM (NOW()-a.login_em))/60 > 30
                  AND COALESCE(l.ligacoes,0) = 0
                """,
                engine,
            )
            relatorio["agentes_improdutivos"] = len(df)
            if not df.empty:
                nomes = ", ".join(df["nome"].tolist()[:5])
                problemas.append(f"👤 *{len(df)} agente(s) sem produção*: {nomes}")
        except Exception as e:
            log.error(f"[Auditoria] Improdutivos: {e}")

        # Campanhas paradas
        try:
            df = pd.read_sql(
                """
                SELECT s.campanha_id, s.campanha,
                       ROUND(EXTRACT(EPOCH FROM (NOW()-MAX(c.iniciada_em)))/60) AS min_parada
                FROM campaign_snapshot s
                LEFT JOIN calls c ON c.campanha_id = s.campanha_id
                WHERE s.captured_at >= NOW() - INTERVAL '10 minutes'
                  AND UPPER(s.status) = 'ACTIVE'
                GROUP BY s.campanha_id, s.campanha
                HAVING MAX(c.iniciada_em) < NOW() - INTERVAL '15 minutes' OR MAX(c.iniciada_em) IS NULL
                """,
                engine,
            )
            relatorio["campanhas_paradas"] = len(df)
            if not df.empty:
                problemas.append(f"📵 *{len(df)} campanha(s) parada(s)*: {', '.join(df['campanha'].tolist())}")
        except Exception as e:
            log.error(f"[Auditoria] Campanhas paradas: {e}")

        # Mailing crítico
        try:
            df = pd.read_sql(
                f"""
                SELECT DISTINCT ON (campanha_id) campanha_id, campanha, mailing_restante_pct
                FROM mailing_status
                WHERE captured_at >= NOW() - INTERVAL '10 minutes'
                  AND mailing_restante_pct < {CFG.LIMITE_MAILING_RESTANTE}
                ORDER BY campanha_id, captured_at DESC
                """,
                engine,
            )
            relatorio["mailing_critico"] = len(df)
            for _, r in df.iterrows():
                problemas.append(
                    f"🔴 Mailing *{r['campanha']}*: apenas *{r['mailing_restante_pct']:.1f}%*"
                )
        except Exception as e:
            log.error(f"[Auditoria] Mailing crítico: {e}")

        if problemas:
            send_webhook_alert(
                "*AUDITORIA " + datetime.now().strftime("%H:%M") + "*\n\n" + "\n\n".join(problemas),
                nivel="ATENCAO", chave="auditoria", throttle_seg=1800,
            )

        relatorio["ts"] = datetime.utcnow().isoformat()
        return relatorio


# ══════════════════════════════════════════════════════════════════════
# 14. REPORT SERVICE
# ══════════════════════════════════════════════════════════════════════

class ReportService:

    @staticmethod
    def pipeline_intraday():
        log.info("[Report] Gerando intraday...")
        os.makedirs("data/reports", exist_ok=True)

        try:
            df_intra = pd.read_sql(
                """
                SELECT campanha,
                       COUNT(*) AS acionamentos,
                       SUM(CASE WHEN tipo_resultado='CPC' THEN 1 ELSE 0 END) AS cpcs,
                       SUM(CASE WHEN tipo_resultado='RPC' THEN 1 ELSE 0 END) AS rpcs,
                       ROUND(AVG(ociosidade_pct),1) AS ociosidade_media,
                       MIN(mailing_restante_pct) AS mailing_restante
                FROM campaign_snapshot
                WHERE DATE(captured_at) = CURRENT_DATE
                GROUP BY campanha ORDER BY acionamentos DESC
                """,
                engine,
            )
        except Exception as e:
            log.error(f"[Report] Erro ao carregar dados: {e}")
            return

        nome = f"data/reports/intraday_{date.today()}_{datetime.now().strftime('%H%M')}.xlsx"
        try:
            df_intra.to_excel(nome, index=False)
        except Exception as e:
            log.error(f"[Report] Erro ao exportar Excel: {e}")

        if not df_intra.empty:
            total_a = int(df_intra["acionamentos"].sum())
            total_c = int(df_intra["cpcs"].sum())
            taxa    = round(total_c / total_a * 100, 1) if total_a else 0
            send_webhook_alert(
                f"*Intraday {datetime.now().strftime('%H:%M')}*\n"
                f"Acionamentos: *{total_a:,}* | CPCs: *{total_c:,}* ({taxa}%)\n"
                f"Campanhas: *{len(df_intra)}*",
                nivel="INFO", chave="relatorio_intraday", forcar=True,
            )


# ══════════════════════════════════════════════════════════════════════
# 15. SCHEDULER
# ══════════════════════════════════════════════════════════════════════

_scheduler = None


def _safe_run(fn, nome: str):
    try:
        fn()
    except Exception:
        log.error(f"[Scheduler] Job '{nome}' falhou:\n{traceback.format_exc()}")


def iniciar_scheduler():
    global _scheduler
    from apscheduler.schedulers.background import BackgroundScheduler
    from apscheduler.events import EVENT_JOB_ERROR
    from apscheduler.triggers.cron import CronTrigger
    from apscheduler.triggers.interval import IntervalTrigger

    _scheduler = BackgroundScheduler(
        job_defaults={"coalesce": True, "max_instances": 1, "misfire_grace_time": 60},
        timezone="America/Sao_Paulo",
    )

    def listener(event):
        if event.exception:
            log.error(f"[Scheduler] Job falhou: {event.job_id}")

    _scheduler.add_listener(listener, EVENT_JOB_ERROR)

    _scheduler.add_job(lambda: _safe_run(ETLService.run_etl, "ETL"),
        IntervalTrigger(minutes=5), id="etl")

    _scheduler.add_job(lambda: _safe_run(OccupancyService.calculate_occupancy, "Ocupação"),
        IntervalTrigger(minutes=1), id="ocupacao")

    _scheduler.add_job(lambda: _safe_run(PacingService.auto_adjust_pacing, "Pacing"),
        IntervalTrigger(minutes=2), id="pacing")

    _scheduler.add_job(lambda: _safe_run(lambda: MailingScoreService.calculate_score(), "Mailing"),
        IntervalTrigger(hours=1), id="mailing")

    _scheduler.add_job(lambda: _safe_run(AuditService.run_audit, "Auditoria"),
        IntervalTrigger(minutes=30), id="auditoria")

    _scheduler.add_job(lambda: _safe_run(ReportService.pipeline_intraday, "Relatório"),
        CronTrigger(minute=0), id="relatorio")

    _scheduler.add_job(lambda: _safe_run(lambda: ForecastService.generate_forecast(), "Forecast"),
        CronTrigger(hour="7,13"), id="forecast")

    _scheduler.add_job(lambda: _safe_run(PacingService.retomar_pos_feriado, "Retomada"),
        CronTrigger(hour=7, minute=55), id="retomada_feriado")

    _scheduler.add_job(lambda: _safe_run(
        lambda: HolidayService.sincronizar_feriados_nacionais(), "Feriados"),
        CronTrigger(month=1, day=1, hour=0, minute=5), id="sync_feriados")

    _scheduler.start()
    log.info(f"[Scheduler] {len(_scheduler.get_jobs())} jobs registrados.")


def parar_scheduler():
    global _scheduler
    if _scheduler:
        _scheduler.shutdown(wait=False)


# ══════════════════════════════════════════════════════════════════════
# 16. API FASTAPI
# ══════════════════════════════════════════════════════════════════════

try:
    from fastapi import Depends, FastAPI, HTTPException, Query, Request, status
    from fastapi.middleware.cors import CORSMiddleware
    from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
    from fastapi.responses import Response
    from jose import JWTError, jwt
    from passlib.context import CryptContext
    from pydantic import BaseModel
    from prometheus_client import Counter, generate_latest, CONTENT_TYPE_LATEST

    pwd_ctx = CryptContext(schemes=["bcrypt"], deprecated="auto")
    oauth2  = OAuth2PasswordBearer(tokenUrl="/auth/token")
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

    class FeriadoIn(BaseModel):
        data:            str
        nome:            str
        tipo:            str = "EMPRESA"
        uf:              Optional[str] = None
        municipio:       Optional[str] = None
        pausar_mailing:  bool = True
        pausar_discagem: bool = True
        pacing_especial: Optional[float] = None
        observacao:      Optional[str] = None

    @asynccontextmanager
    async def lifespan(app: FastAPI):
        log.info("=== Agente IA Control Desk iniciando ===")
        CFG.validar_seguranca()
        iniciar_scheduler()
        yield
        parar_scheduler()

    app = FastAPI(
        title="Agente IA Control Desk",
        version="2.0.0",
        lifespan=lifespan,
    )
    app.add_middleware(
        CORSMiddleware,
        allow_origins=CFG.CORS_ORIGINS_LIST,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    @app.middleware("http")
    async def _contar_requisicoes(request: Request, call_next):
        # Usa a rota declarada (ex.: /feriados/{feriado_id}) para não explodir
        # a cardinalidade da métrica com IDs; cai para o path cru se não houver.
        response = await call_next(request)
        rota = request.scope.get("route")
        endpoint = getattr(rota, "path", None) or request.url.path
        REQ_COUNT.labels(endpoint=endpoint).inc()
        return response

    # ── Auth
    @app.post("/auth/token", tags=["Auth"])
    def login(form: OAuth2PasswordRequestForm = Depends()):
        rows = executar_query(
            "SELECT hashed_pw, role FROM api_users WHERE username = :u AND ativo = TRUE",
            {"u": form.username},
        )
        if not rows or not pwd_ctx.verify(form.password, rows[0]["hashed_pw"]):
            raise HTTPException(status_code=400, detail="Usuário ou senha incorretos")
        return {"access_token": _criar_token({"sub": form.username, "role": rows[0]["role"]}), "token_type": "bearer"}

    # ── Sistema
    @app.get("/", tags=["Sistema"])
    def health():
        return {"status": "running", "versao": "2.0.0", "banco": testar_conexao()}

    @app.get("/metrics", tags=["Sistema"])
    def metrics():
        return Response(generate_latest(), media_type=CONTENT_TYPE_LATEST)

    # ── ETL
    @app.post("/etl/run", tags=["ETL"], dependencies=[Depends(_verificar_token)])
    def run_etl():
        return {"resultado": ETLService.run_etl()}

    # ── Ocupação
    @app.get("/ocupacao", tags=["Ocupação"], dependencies=[Depends(_verificar_token)])
    def ocupacao():
        return OccupancyService.calculate_occupancy()

    @app.get("/ocupacao/campanhas", tags=["Ocupação"], dependencies=[Depends(_verificar_token)])
    def ocupacao_campanhas():
        df = OccupancyService.por_campanha()
        return df.to_dict("records") if not df.empty else []

    # ── Pacing
    @app.post("/pacing/ajustar", tags=["Pacing"], dependencies=[Depends(_verificar_token)])
    def ajustar_pacing():
        return {"resultado": PacingService.auto_adjust_pacing()}

    @app.get("/pacing/historico", tags=["Pacing"], dependencies=[Depends(_verificar_token)])
    def historico_pacing(campanha_id: Optional[str] = Query(None), horas: int = Query(24)):
        sql = "SELECT * FROM pacing_audit_log WHERE ts >= NOW() - INTERVAL :h"
        params = {"h": f"{horas} hours"}
        if campanha_id:
            sql += " AND campanha_id = :cid"
            params["cid"] = campanha_id
        sql += " ORDER BY ts DESC LIMIT 500"
        return executar_query(sql, params)

    # ── Mailing
    @app.get("/mailing/top", tags=["Mailing"], dependencies=[Depends(_verificar_token)])
    def top_mailing(n: int = Query(100), campanha_id: Optional[str] = Query(None)):
        sql = "SELECT * FROM mailing_scored"
        params = {}
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

    # ── Feriados
    @app.get("/feriados", tags=["Feriados"], dependencies=[Depends(_verificar_token)])
    def listar_feriados(ano: int = Query(None)):
        return HolidayService.listar_feriados(ano=ano)

    @app.post("/feriados", tags=["Feriados"], dependencies=[Depends(_requer_admin)])
    def adicionar_feriado(body: FeriadoIn, payload: dict = Depends(_verificar_token)):
        try:
            data_f = date.fromisoformat(body.data)
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
    def sincronizar_feriados(ano: int = Query(None)):
        n = HolidayService.sincronizar_feriados_nacionais(ano=ano)
        return {"sincronizados": n}

    @app.get("/feriados/proximos", tags=["Feriados"], dependencies=[Depends(_verificar_token)])
    def proximos_feriados(dias: int = Query(30)):
        return HolidayService.proximos_feriados(dias=dias)

    # ── Forecast
    @app.get("/forecast", tags=["Forecast"], dependencies=[Depends(_verificar_token)])
    def ultimo_forecast():
        try:
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

    # ── Auditoria
    @app.post("/auditoria/executar", tags=["Auditoria"], dependencies=[Depends(_verificar_token)])
    def executar_auditoria():
        return AuditService.run_audit()

    # ── Alertas
    @app.get("/alertas", tags=["Alertas"], dependencies=[Depends(_verificar_token)])
    def historico_alertas(nivel: Optional[str] = Query(None), limite: int = Query(50)):
        sql = "SELECT * FROM alert_log"
        params = {}
        if nivel:
            sql += " WHERE nivel = :nivel"
            params["nivel"] = nivel.upper()
        sql += " ORDER BY ts DESC LIMIT :lim"
        params["lim"] = limite
        return executar_query(sql, params)

    # ── Campanhas
    @app.get("/campanhas/config", tags=["Campanhas"], dependencies=[Depends(_verificar_token)])
    def config_campanhas():
        return executar_query("SELECT * FROM campaign_config WHERE ativo = TRUE ORDER BY campanha_nome")

    FASTAPI_DISPONIVEL = True

except ImportError:
    log.warning("FastAPI não instalado — API desativada. Rode: pip install fastapi uvicorn")
    app = None
    FASTAPI_DISPONIVEL = False


# ══════════════════════════════════════════════════════════════════════
# 17. DASHBOARD STREAMLIT
# ══════════════════════════════════════════════════════════════════════

def rodar_dashboard():
    """Execute com: streamlit run agente_ia_control_desk.py"""
    try:
        import streamlit as st
        import plotly.express as px
        import plotly.graph_objects as go
    except ImportError:
        print("Streamlit/Plotly não instalados. Rode: pip install streamlit plotly")
        return

    st.set_page_config(page_title="Control Desk IA", page_icon="🤖", layout="wide")

    with st.sidebar:
        st.title("🤖 Control Desk IA")
        st.caption(f"v2.0.0 | {datetime.now().strftime('%d/%m/%Y %H:%M')}")
        banco_ok = testar_conexao()
        st.markdown(f"**Banco:** {'🟢 Conectado' if banco_ok else '🔴 Offline'}")
        st.divider()
        try:
            camps = pd.read_sql("SELECT DISTINCT campanha FROM campaign_snapshot ORDER BY campanha", engine)
            camp_lista = ["Todas"] + camps["campanha"].tolist()
        except Exception:
            camp_lista = ["Todas"]
        camp_filtro = st.selectbox("🎯 Campanha", camp_lista)
        auto_refresh = st.toggle("⟳ Auto-refresh 30s", value=True)
        if st.button("🔄 Atualizar"):
            st.rerun()

    def _q(sql, params=None):
        try:
            return pd.read_sql(sql, engine, params=params)
        except Exception as e:
            return pd.DataFrame()

    aba1, aba2, aba3, aba4, aba5, aba6 = st.tabs([
        "📊 Tempo Real", "📋 Campanhas", "⚙️ Pacing Log",
        "📈 Forecast", "🗓️ Feriados", "🔍 Auditoria"
    ])

    # ── Aba 1: Tempo Real
    with aba1:
        st.subheader("Visão em Tempo Real")
        df_ag = _q("SELECT * FROM agents WHERE captured_at >= NOW() - INTERVAL '6 minutes'")
        if not df_ag.empty:
            df_ag["status_norm"] = df_ag["status"].str.lower().str.strip()
            total    = len(df_ag)
            ociosos  = int(df_ag["status_norm"].isin(STATUS_OCIOSO).sum())
            em_pausa = int(df_ag["status_norm"].isin(STATUS_PAUSA).sum())
            em_lig   = int(df_ag["status_norm"].isin(STATUS_LIGANDO).sum())
            ocio_pct = round(ociosos / total * 100, 1) if total else 0
            c1,c2,c3,c4,c5 = st.columns(5)
            c1.metric("👥 Logados",   total)
            c2.metric("📞 Em ligação", em_lig)
            c3.metric("✅ Disponíveis", ociosos, delta=f"{ocio_pct}% ociosos")
            c4.metric("⏸️ Em pausa", em_pausa)
            c5.metric("📊 Ocupação", f"{round((total-ociosos)/total*100,1) if total else 0}%")

        st.divider()
        df_ml = _q("SELECT DISTINCT ON (campanha_id) campanha, mailing_restante_pct FROM mailing_status WHERE captured_at >= NOW() - INTERVAL '10 minutes' ORDER BY campanha_id, captured_at DESC")
        if not df_ml.empty:
            st.subheader("📬 Mailing")
            for _, r in df_ml.iterrows():
                st.progress(int(r["mailing_restante_pct"]), text=f"{r['campanha']} — {r['mailing_restante_pct']:.1f}%")

        st.divider()
        df_al = _q("SELECT nivel, mensagem, ts FROM alert_log ORDER BY ts DESC LIMIT 10")
        st.subheader("🔔 Alertas Recentes")
        if df_al.empty:
            st.info("Nenhum alerta.")
        else:
            for _, r in df_al.iterrows():
                icone = {"CRITICO": "🔴", "ATENCAO": "⚠️", "INFO": "ℹ️"}.get(r["nivel"], "📢")
                ts = pd.to_datetime(r["ts"]).strftime("%H:%M:%S")
                st.markdown(f"`{ts}` {icone} **[{r['nivel']}]** {r['mensagem']}")

    # ── Aba 2: Campanhas
    with aba2:
        st.subheader("Desempenho por Campanha")
        sql = "SELECT campanha, MAX(agentes_logados) AS agentes, AVG(ociosidade_pct) AS ociosidade, AVG(abandono_pct) AS abandono, MIN(mailing_restante_pct) AS mailing_restante, AVG(pacing_atual) AS pacing_medio FROM campaign_snapshot WHERE DATE(captured_at) = CURRENT_DATE"
        params = {}
        if camp_filtro != "Todas":
            sql += " AND campanha = :camp"
            params["camp"] = camp_filtro
        sql += " GROUP BY campanha ORDER BY campanha"
        df_c = _q(sql, params)
        if not df_c.empty:
            st.dataframe(df_c.round(1), use_container_width=True, hide_index=True)
            fig = px.bar(df_c, x="campanha", y="ociosidade", title="Ociosidade por Campanha (%)", color="ociosidade", color_continuous_scale=["green","yellow","red"])
            st.plotly_chart(fig, use_container_width=True)

    # ── Aba 3: Pacing Log
    with aba3:
        st.subheader("Histórico de Ajustes de Pacing")
        df_p = _q("SELECT campanha_nome, pacing_anterior, pacing_novo, motivo, ocupacao_pct, bloqueado, motivo_bloqueio, ts FROM pacing_audit_log WHERE ts >= NOW() - INTERVAL '24 hours' ORDER BY ts DESC LIMIT 200")
        if not df_p.empty:
            c1,c2,c3 = st.columns(3)
            c1.metric("Total", len(df_p))
            c2.metric("Efetivados", int((~df_p["bloqueado"]).sum()))
            c3.metric("Bloqueados", int(df_p["bloqueado"].sum()))
            df_p["status"] = df_p["bloqueado"].map({True: "🔒 Bloqueado", False: "✅ Ajustado"})
            st.dataframe(df_p, use_container_width=True, hide_index=True)

    # ── Aba 4: Forecast
    with aba4:
        st.subheader("Previsão de Volume")
        df_fc = _q("SELECT ds, yhat, yhat_lower, yhat_upper, agentes_necessarios FROM forecast_calls WHERE gerado_em=(SELECT MAX(gerado_em) FROM forecast_calls) ORDER BY ds")
        if not df_fc.empty:
            df_fc["ds"] = pd.to_datetime(df_fc["ds"])
            c1,c2 = st.columns(2)
            c1.metric("Pico previsto", f"{int(df_fc['yhat'].max())} chamadas")
            c2.metric("Agentes no pico", f"{int(df_fc['agentes_necessarios'].max())}")
            fig = px.line(df_fc, x="ds", y="yhat", title="Volume Previsto por Hora")
            st.plotly_chart(fig, use_container_width=True)
            fig2 = px.bar(df_fc, x="ds", y="agentes_necessarios", title="Agentes Necessários", color="agentes_necessarios", color_continuous_scale=["green","yellow","red"])
            st.plotly_chart(fig2, use_container_width=True)
        else:
            st.info("Nenhuma previsão gerada. Use POST /forecast/gerar")

    # ── Aba 5: Feriados
    with aba5:
        st.subheader("🗓️ Gestão de Feriados e Datas Especiais")
        df_prox = _q("SELECT data, nome, tipo, pausar_mailing, pausar_discagem FROM feriados WHERE data BETWEEN CURRENT_DATE AND CURRENT_DATE + 30 ORDER BY data")
        if not df_prox.empty:
            st.warning(f"⚠️ **{len(df_prox)} feriado(s) nos próximos 30 dias**")
            for _, r in df_prox.iterrows():
                d = pd.to_datetime(r["data"]).strftime("%d/%m/%Y")
                acoes = []
                if r["pausar_mailing"]:  acoes.append("pausa mailing")
                if r["pausar_discagem"]: acoes.append("pausa discagem")
                st.markdown(f"  - **{d}** — {r['nome']} `{r['tipo']}` → {', '.join(acoes) or 'sem pausa'}")

        st.divider()
        st.subheader("Cadastrar novo feriado")
        with st.form("form_feriado", clear_on_submit=True):
            col1, col2 = st.columns(2)
            with col1:
                data_f  = st.date_input("Data", value=date.today())
                nome_f  = st.text_input("Nome", placeholder="Ex: Aniversário da cidade")
                tipo_f  = st.selectbox("Tipo", ["EMPRESA","MUNICIPAL","ESTADUAL","NACIONAL"])
            with col2:
                uf_f    = st.text_input("UF (estadual/municipal)", max_chars=2)
                mun_f   = st.text_input("Município")
                obs_f   = st.text_input("Observação")
            col3, col4 = st.columns(2)
            with col3:
                pausar_m = st.checkbox("Pausar mailing", value=True)
                pausar_d = st.checkbox("Pausar discagem", value=True)
            with col4:
                pac_esp = st.number_input("Pacing especial (0=sem restrição)", min_value=0.0, max_value=10.0, value=0.0)

            if st.form_submit_button("➕ Adicionar"):
                if nome_f.strip():
                    ok = HolidayService.adicionar_feriado(
                        data_f=data_f, nome=nome_f, tipo=tipo_f,
                        uf=uf_f or None, municipio=mun_f or None,
                        pausar_mailing=pausar_m, pausar_discagem=pausar_d,
                        pacing_especial=pac_esp if pac_esp > 0 else None,
                        observacao=obs_f or None, criado_por="Dashboard",
                    )
                    if ok:
                        st.success(f"✅ '{nome_f}' cadastrado para {data_f.strftime('%d/%m/%Y')}")
                        st.rerun()
                    else:
                        st.error("Erro ao salvar.")
                else:
                    st.error("Informe o nome do feriado.")

        st.divider()
        ano_sel = st.selectbox("Ano", [date.today().year, date.today().year + 1])
        df_fer = _q("SELECT id, data, nome, tipo, uf, pausar_mailing, pausar_discagem FROM feriados WHERE EXTRACT(YEAR FROM data) = :ano ORDER BY data", {"ano": ano_sel})
        if not df_fer.empty:
            df_fer["data"] = pd.to_datetime(df_fer["data"]).dt.strftime("%d/%m/%Y")
            df_fer["pausar_mailing"]  = df_fer["pausar_mailing"].map({True: "✅", False: "❌"})
            df_fer["pausar_discagem"] = df_fer["pausar_discagem"].map({True: "✅", False: "❌"})
            st.dataframe(df_fer, use_container_width=True, hide_index=True)
            id_rem = st.number_input("ID para remover (0=nenhum)", min_value=0, step=1)
            if st.button("🗑️ Remover") and id_rem > 0:
                if HolidayService.remover_feriado(int(id_rem)):
                    st.success(f"Feriado id={id_rem} removido.")
                    st.rerun()
                else:
                    st.error("ID não encontrado.")

    # ── Aba 6: Auditoria
    with aba6:
        st.subheader("🔍 Auditoria Operacional")
        if st.button("▶️ Executar auditoria"):
            with st.spinner("Executando..."):
                resultado = AuditService.run_audit()
            st.success("Concluída!")
            st.json(resultado)

        st.divider()
        st.subheader("Agentes sem produção (>30 min logados)")
        df_imp = _q("SELECT a.nome, a.campanha, ROUND(EXTRACT(EPOCH FROM (NOW()-a.login_em))/60) AS min_logado, COALESCE(l.ligacoes,0) AS ligacoes FROM agents a LEFT JOIN (SELECT agente_id, COUNT(*) AS ligacoes FROM calls WHERE DATE(iniciada_em)=CURRENT_DATE GROUP BY agente_id) l ON a.agente_id=l.agente_id WHERE a.captured_at>=NOW()-INTERVAL '5 minutes' AND LOWER(a.status) NOT IN ('paused','offline') AND COALESCE(l.ligacoes,0)=0 AND EXTRACT(EPOCH FROM (NOW()-a.login_em))/60>30")
        if df_imp.empty:
            st.success("Nenhum agente improdutivo.")
        else:
            st.warning(f"{len(df_imp)} agente(s) improdutivo(s)")
            st.dataframe(df_imp, use_container_width=True, hide_index=True)

    if auto_refresh:
        time.sleep(30)
        st.rerun()


# ══════════════════════════════════════════════════════════════════════
# 18. ENTRYPOINT
# ══════════════════════════════════════════════════════════════════════

if __name__ == "__main__":
    import sys

    if len(sys.argv) > 1 and sys.argv[1] == "dashboard":
        # python agente_ia_control_desk.py dashboard
        rodar_dashboard()
    elif len(sys.argv) > 1 and sys.argv[1] == "api":
        # python agente_ia_control_desk.py api
        import uvicorn
        uvicorn.run("agente_ia_control_desk:app", host="0.0.0.0", port=8000, reload=True)
    else:
        # python agente_ia_control_desk.py  → modo standalone com scheduler
        log.info("🚀 Iniciando Agente IA Control Desk — modo standalone")
        CFG.validar_seguranca()
        send_webhook_alert("🤖 Agente IA Control Desk iniciado.", nivel="INFO", chave="startup", forcar=True)
        iniciar_scheduler()
        log.info("Scheduler rodando. Pressione Ctrl+C para encerrar.")
        try:
            while True:
                time.sleep(30)
        except KeyboardInterrupt:
            parar_scheduler()
            log.info("Agente encerrado.")
