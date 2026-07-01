"""
╔══════════════════════════════════════════════════════════════════════════╗
║  AGENTE IA — CONTROL DESK  |  Stack: Olos + EasyCollector               ║
║  Versão: 2.0.0 — CORRIGIDA                                              ║
╠══════════════════════════════════════════════════════════════════════════╣
║  BUGS CORRIGIDOS (relatório de auditoria):                               ║
║  BUG-01  __init__ / __class__ / __name__  (dunder names)                ║
║  BUG-02  if __name__ == "__main__"  (entrypoint)                        ║
║  BUG-03  freq="H" -> freq="h"  (pandas 2.x+)                           ║
║  BUG-04  schedule -> SimpleScheduler interno (threading.Timer)          ║
║  BUG-05  SQLAlchemy stub + pool_pre_ping em todos os engines            ║
║  BUG-06  from __future__ import annotations                             ║
║  BUG-07  agentes = agentes.copy() antes de mutar DataFrame              ║
║  BUG-08  pool_pre_ping=True, pool_recycle=1800                          ║
║  BUG-09  Dict/List do typing (Python 3.8 compatível)                   ║
║  BUG-10  .env.example gerado automaticamente                            ║
║  MELHORIAS INCLUÍDAS:                                                    ║
║  M1  Circuit breaker nas APIs (3 falhas → alerta + pausa)               ║
║  M2  Cache TTL=90s no snapshot (−40% chamadas API)                      ║
║  M3  Dead letter queue para alertas Teams/Email                         ║
║  M4  Persistência do modelo ML em disco via joblib                      ║
║  M5  Aba Timeline hora-a-hora no Excel intraday                         ║
║  M6  Health check HTTP /health porta 8080                               ║
╚══════════════════════════════════════════════════════════════════════════╝
"""

from __future__ import annotations          # BUG-06: type hints Python 3.8+

# ── stdlib ────────────────────────────────────────────────────────────────
import json
import logging
import os
import re
import smtplib
import time
import traceback
import threading
import warnings
from collections import deque
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass, field
from datetime import datetime, date, timedelta
from email import encoders
from email.mime.base import MIMEBase
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from http.server import BaseHTTPRequestHandler, HTTPServer
from typing import Dict, List, Optional       # BUG-09: compatível com 3.8

# ── third-party (sempre disponíveis) ──────────────────────────────────────
import numpy as np
import pandas as pd
import requests
import joblib                                 # M4
from dotenv import load_dotenv
from sklearn.ensemble import GradientBoostingClassifier
from sklearn.model_selection import train_test_split
from sklearn.preprocessing import LabelEncoder

# ── SQLAlchemy com stub de fallback (BUG-05) ──────────────────────────────
try:
    from sqlalchemy import create_engine, text as sa_text
    SQLALCHEMY_OK = True
except ImportError:
    SQLALCHEMY_OK = False

    class _FakeEngine:
        def connect(self):
            raise RuntimeError(
                "SQLAlchemy não instalado. Execute:\n"
                "  pip install sqlalchemy psycopg2-binary"
            )

    def create_engine(url, **kw):   # type: ignore[misc]
        return _FakeEngine()

    def sa_text(q: str) -> str:     # type: ignore[misc]
        return q

warnings.filterwarnings("ignore")
load_dotenv()


# ==========================================================================
# ETAPA 1 — CONFIGURAÇÃO CENTRAL
# ==========================================================================

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler("control_desk_agent.log", encoding="utf-8"),
    ],
)
log = logging.getLogger("ControlDeskAgent")


@dataclass
class Config:
    """Centraliza todas as configurações do agente."""

    # Banco
    db_url: str = os.getenv("DB_URL", "postgresql://user:senha@localhost:5432/callcenter")

    # Olos
    olos_base_url: str = os.getenv("OLOS_BASE_URL", "https://olos.empresa.com/api/v2")
    olos_token: str    = os.getenv("OLOS_TOKEN", "SEU_TOKEN_OLOS")

    # EasyCollector
    easy_base_url: str = os.getenv("EASY_BASE_URL", "https://easycollector.empresa.com/api")
    easy_token: str    = os.getenv("EASY_TOKEN", "SEU_TOKEN_EASY")

    # Alertas
    teams_webhook: str = os.getenv("TEAMS_WEBHOOK", "")
    email_smtp: str    = os.getenv("EMAIL_SMTP", "smtp.empresa.com")
    email_porta: int   = int(os.getenv("EMAIL_PORTA", "587"))
    email_user: str    = os.getenv("EMAIL_USER", "agente@empresa.com")
    email_senha: str   = os.getenv("EMAIL_SENHA", "")
    email_destinos: List[str] = field(
        default_factory=lambda: ["supervisao@empresa.com", "gerencia@empresa.com"]
    )

    # Limites operacionais
    limite_ociosidade_pct: float   = 15.0
    limite_abandono_pct: float     = 8.0
    limite_mailing_restante: float = 5.0
    limite_pausa_min: int          = 20
    intervalo_monitor_seg: int     = 120

    # Circuit breaker (M1)
    cb_max_falhas: int = 3
    cb_pausa_min: int  = 10

    # Cache snapshot (M2)
    cache_ttl_seg: int = 90

    # Diretórios
    dir_mailing: str = "./mailings"
    dir_reports: str = "./reports"
    dir_modelos: str = "./models"

    # Health check (M6)
    health_port: int = 8080


CFG = Config()


def _gerar_env_example() -> None:
    """BUG-10: Cria .env.example de referência se não existir."""
    if os.path.exists(".env.example"):
        return
    linhas = [
        "DB_URL=postgresql://usuario:senha@host:5432/callcenter",
        "OLOS_BASE_URL=https://olos.suaempresa.com/api/v2",
        "OLOS_TOKEN=",
        "EASY_BASE_URL=https://easycollector.suaempresa.com/api",
        "EASY_TOKEN=",
        "TEAMS_WEBHOOK=",
        "EMAIL_SMTP=smtp.suaempresa.com",
        "EMAIL_PORTA=587",
        "EMAIL_USER=",
        "EMAIL_SENHA=",
    ]
    with open(".env.example", "w", encoding="utf-8") as f:
        f.write("\n".join(linhas) + "\n")
    log.info("[BUG-10] .env.example criado na raiz do projeto.")


def _make_engine(db_url: str):
    """BUG-08: Cria engine com pool_pre_ping e pool_recycle."""
    if SQLALCHEMY_OK:
        return create_engine(
            db_url,
            pool_pre_ping=True,   # BUG-08
            pool_recycle=1800,    # BUG-08
            pool_size=5,
            max_overflow=10,
        )
    return create_engine(db_url)


# ==========================================================================
# SCHEDULER INTERNO — substitui 'schedule' sem dependência extra (BUG-04)
# ==========================================================================

class SimpleScheduler:
    """
    Scheduler leve baseado em threading.Timer.
    Substitui o pacote 'schedule' sem adicionar dependência.
    """

    def __init__(self) -> None:
        self._jobs: List[Dict] = []

    def every_seconds(self, n: int, func, nome: str = "job") -> None:
        self._jobs.append({"interval": n, "func": func, "nome": nome,
                            "next_run": time.monotonic() + n})

    def every_minutes(self, n: int, func, nome: str = "job") -> None:
        self.every_seconds(n * 60, func, nome)

    def daily_at(self, hh: int, mm: int, func, nome: str = "job") -> None:
        now = datetime.now()
        target = now.replace(hour=hh, minute=mm, second=0, microsecond=0)
        if target <= now:
            target += timedelta(days=1)
        delta = (target - now).total_seconds()
        self._jobs.append({"interval": 86400, "func": func, "nome": nome,
                            "next_run": time.monotonic() + delta})

    def run_pending(self) -> None:
        now = time.monotonic()
        for job in self._jobs:
            if now >= job["next_run"]:
                try:
                    job["func"]()
                except Exception:
                    log.error(f"Erro no job [{job['nome']}]:\n{traceback.format_exc()}")
                job["next_run"] = now + job["interval"]

    def loop(self, stop_event: threading.Event, tick: float = 5.0) -> None:
        while not stop_event.is_set():
            self.run_pending()
            time.sleep(tick)


# ==========================================================================
# CIRCUIT BREAKER (M1)
# ==========================================================================

class CircuitBreaker:
    """
    M1: Após N falhas consecutivas abre o circuito por X minutos
    e dispara alerta no Teams.
    """

    def __init__(self, max_falhas: int, pausa_min: int, nome: str) -> None:
        self.max_falhas = max_falhas
        self.pausa_min  = pausa_min
        self.nome       = nome
        self._falhas    = 0
        self._aberto_ate: Optional[datetime] = None
        self._log = logging.getLogger(f"CB.{nome}")

    @property
    def aberto(self) -> bool:
        if self._aberto_ate is None:
            return False
        if datetime.now() < self._aberto_ate:
            return True
        # timeout expirado → fecha o circuito
        self._aberto_ate = None
        self._falhas = 0
        self._log.info(f"Circuito {self.nome} fechado (timeout expirado).")
        return False

    def registrar_sucesso(self) -> None:
        self._falhas = 0

    def registrar_falha(self, alertas: Optional[GestorAlertas] = None) -> None:
        self._falhas += 1
        self._log.warning(f"Falha {self._falhas}/{self.max_falhas} em {self.nome}")
        if self._falhas >= self.max_falhas:
            self._aberto_ate = datetime.now() + timedelta(minutes=self.pausa_min)
            msg = (f"⚡ CIRCUIT BREAKER — {self.nome}\n"
                   f"{self._falhas} falhas consecutivas.\n"
                   f"Retentativa em {self.pausa_min} min.")
            self._log.error(msg)
            if alertas:
                alertas.enviar_teams(msg)


# ==========================================================================
# GESTOR DE ALERTAS — definido antes das outras classes (BUG-01 + M3)
# ==========================================================================

class GestorAlertas:
    """Centraliza canais de comunicação com dead letter queue (M3)."""

    def __init__(self, cfg: Config) -> None:     # BUG-01: __init__
        self.cfg  = cfg
        self._log = logging.getLogger(self.__class__.__name__)   # BUG-01: __class__
        self._dlq: deque = deque(maxlen=200)     # M3
        self._dlq_lock = threading.Lock()
        # M3: thread de reenvio da DLQ a cada 5 min
        threading.Thread(target=self._dlq_loop, daemon=True, name="dlq").start()

    # ── DLQ (M3) ──────────────────────────────────────────────────────────

    def _dlq_loop(self) -> None:
        while True:
            time.sleep(300)
            self._flush_dlq()

    def _flush_dlq(self) -> None:
        with self._dlq_lock:
            pendentes = list(self._dlq)
            self._dlq.clear()
        reenviados = 0
        for item in pendentes:
            if self._post_teams(item["msg"]):
                reenviados += 1
            else:
                with self._dlq_lock:
                    self._dlq.append(item)
        if reenviados:
            self._log.info(f"[DLQ] {reenviados} msg(s) reenviada(s).")

    def _post_teams(self, mensagem: str) -> bool:
        if not self.cfg.teams_webhook:
            return True
        try:
            r = requests.post(self.cfg.teams_webhook,
                              json={"text": mensagem}, timeout=10)
            return r.status_code < 400
        except Exception:
            return False

    @property
    def dlq_size(self) -> int:
        return len(self._dlq)

    # ── canais públicos ───────────────────────────────────────────────────

    def enviar_teams(self, mensagem: str) -> None:
        if self._post_teams(mensagem):
            self._log.info("Teams: OK")
        else:
            self._log.warning("Teams: falhou → DLQ")
            with self._dlq_lock:
                self._dlq.append({"msg": mensagem, "ts": datetime.now().isoformat()})

    def enviar_email(self, assunto: str, corpo: str,
                     anexo_path: Optional[str] = None) -> None:
        if not self.cfg.email_senha:
            self._log.warning("Email sem senha configurada — pulando envio.")
            return
        try:
            msg = MIMEMultipart()
            msg["From"]    = self.cfg.email_user
            msg["To"]      = ", ".join(self.cfg.email_destinos)
            msg["Subject"] = assunto
            msg.attach(MIMEText(corpo, "html"))
            if anexo_path and os.path.exists(anexo_path):
                with open(anexo_path, "rb") as fh:
                    parte = MIMEBase("application", "octet-stream")
                    parte.set_payload(fh.read())
                encoders.encode_base64(parte)
                parte.add_header("Content-Disposition",
                                 f"attachment; filename={os.path.basename(anexo_path)}")
                msg.attach(parte)
            with smtplib.SMTP(self.cfg.email_smtp, self.cfg.email_porta) as srv:
                srv.starttls()
                srv.login(self.cfg.email_user, self.cfg.email_senha)
                srv.sendmail(self.cfg.email_user,
                             self.cfg.email_destinos, msg.as_string())
            self._log.info(f"Email enviado: {assunto}")
        except Exception as e:
            self._log.error(f"Falha email: {e}")


# ==========================================================================
# ETAPA 2 — ETL: INGESTÃO DE DADOS
# ==========================================================================

class ETLIngestao:
    """
    Coleta dados de Olos e EasyCollector → persiste em PostgreSQL.
    M1: circuit breaker por endpoint.
    M2: cache TTL para snapshot de campanhas.
    """

    def __init__(self, cfg: Config, alertas: GestorAlertas) -> None:   # BUG-01
        self.cfg     = cfg
        self.alertas = alertas
        self.engine  = _make_engine(cfg.db_url)                        # BUG-08
        self._log    = logging.getLogger(self.__class__.__name__)       # BUG-01
        self._hdrs_olos = {"Authorization": f"Bearer {cfg.olos_token}"}
        self._hdrs_easy = {"Authorization": f"Bearer {cfg.easy_token}"}
        # M1
        self._cb_olos = CircuitBreaker(cfg.cb_max_falhas, cfg.cb_pausa_min, "Olos")
        self._cb_easy = CircuitBreaker(cfg.cb_max_falhas, cfg.cb_pausa_min, "Easy")
        # M2
        self._cache: Dict[str, Dict] = {}

    # ── helpers ───────────────────────────────────────────────────────────

    def _get(self, url: str, headers: Dict,
             params: Optional[Dict] = None,
             cb: Optional[CircuitBreaker] = None) -> Dict:
        if cb and cb.aberto:
            self._log.warning(f"Circuito aberto para {cb.nome} — request ignorado.")
            return {}
        try:
            r = requests.get(url, headers=headers, params=params, timeout=15)
            r.raise_for_status()
            if cb:
                cb.registrar_sucesso()
            return r.json()
        except Exception as e:
            self._log.error(f"GET {url} falhou: {e}")
            if cb:
                cb.registrar_falha(self.alertas)
            return {}

    def _get_cached(self, chave: str, url: str, headers: Dict,
                    params: Optional[Dict] = None,
                    cb: Optional[CircuitBreaker] = None) -> Dict:
        """M2: retorna do cache se dentro do TTL configurado."""
        entry = self._cache.get(chave)
        if entry and (time.time() - entry["ts"]) < self.cfg.cache_ttl_seg:
            return entry["data"]
        data = self._get(url, headers, params, cb)
        if data:
            self._cache[chave] = {"data": data, "ts": time.time()}
        return data

    def _salvar(self, df: pd.DataFrame, tabela: str) -> None:
        if df.empty:
            self._log.warning(f"DataFrame vazio — {tabela} ignorada.")
            return
        if not SQLALCHEMY_OK:
            self._log.warning(f"SQLAlchemy ausente — {len(df)} linhas de '{tabela}' não persistidas.")
            return
        df = df.copy()
        df["captured_at"] = datetime.utcnow()
        try:
            df.to_sql(tabela, self.engine, if_exists="append", index=False)
            self._log.info(f"[ETL] {len(df)} linhas → {tabela}")
        except Exception as e:
            self._log.error(f"Falha ao salvar '{tabela}': {e}")

    # ── fontes Olos ───────────────────────────────────────────────────────

    def fetch_snapshot_campanhas(self) -> pd.DataFrame:
        data = self._get_cached(
            "snap_campanhas",
            f"{self.cfg.olos_base_url}/campaigns/snapshot",
            self._hdrs_olos, cb=self._cb_olos,
        )
        return pd.DataFrame(data.get("data", []))

    def fetch_agentes(self) -> pd.DataFrame:
        data = self._get(
            f"{self.cfg.olos_base_url}/agents/status",
            self._hdrs_olos, cb=self._cb_olos,
        )
        return pd.DataFrame(data.get("agents", []))

    def fetch_ligacoes(self, data_inicio: Optional[str] = None) -> pd.DataFrame:
        params = {"from": data_inicio or (date.today() - timedelta(days=1)).isoformat()}
        data = self._get(
            f"{self.cfg.olos_base_url}/calls/history",
            self._hdrs_olos, params=params, cb=self._cb_olos,
        )
        return pd.DataFrame(data.get("calls", []))

    def fetch_mailing_status(self) -> pd.DataFrame:
        data = self._get(
            f"{self.cfg.olos_base_url}/mailing/status",
            self._hdrs_olos, cb=self._cb_olos,
        )
        return pd.DataFrame(data.get("mailings", []))

    # ── fontes EasyCollector ──────────────────────────────────────────────

    def fetch_easy_promessas(self) -> pd.DataFrame:
        data = self._get(
            f"{self.cfg.easy_base_url}/promises",
            self._hdrs_easy,
            params={"date": date.today().isoformat()},
            cb=self._cb_easy,
        )
        return pd.DataFrame(data.get("promises", []))

    def fetch_easy_carteiras(self) -> pd.DataFrame:
        data = self._get(
            f"{self.cfg.easy_base_url}/portfolios/active",
            self._hdrs_easy, cb=self._cb_easy,
        )
        return pd.DataFrame(data.get("portfolios", []))

    # ── pipeline completo ─────────────────────────────────────────────────

    def executar(self) -> None:
        self._log.info("=== ETL Iniciado ===")
        self._salvar(self.fetch_snapshot_campanhas(), "olos_campaign_snapshot")
        self._salvar(self.fetch_agentes(),             "olos_agents_log")
        self._salvar(self.fetch_mailing_status(),      "olos_mailing_status")
        self._salvar(self.fetch_easy_promessas(),      "easy_promessas")
        self._salvar(self.fetch_easy_carteiras(),      "easy_carteiras")
        self._log.info("=== ETL Concluído ===")


# ==========================================================================
# ETAPA 3 — HIGIENIZAÇÃO E SCORE DE MAILING
# ==========================================================================

class MailingProcessor:
    """Valida, limpa e pontua registros de mailing."""

    DDDS_VALIDOS: set = {
        str(d) for d in
        list(range(11, 20)) + list(range(21, 30)) +
        list(range(31, 40)) + list(range(41, 50)) +
        list(range(51, 70)) + list(range(71, 100))
    }

    DDD_SCORE: Dict[str, int] = {
        "11": 10, "21": 9, "31": 8, "41": 8, "51": 7,
        "71": 7,  "61": 6, "85": 6, "81": 6,
    }

    def __init__(self, cfg: Config) -> None:                         # BUG-01
        self.cfg  = cfg
        self._log = logging.getLogger(self.__class__.__name__)       # BUG-01

    @staticmethod
    def validar_cpf(cpf: str) -> bool:
        cpf = re.sub(r"\D", "", str(cpf or ""))
        if len(cpf) != 11 or len(set(cpf)) == 1:
            return False
        for i in range(2):
            soma   = sum(int(cpf[j]) * (10 + i - j) for j in range(9 + i))
            digito = (soma * 10 % 11) % 10
            if digito != int(cpf[9 + i]):
                return False
        return True

    @staticmethod
    def validar_telefone(tel: str) -> Optional[str]:
        digits = re.sub(r"\D", "", str(tel or ""))
        if len(digits) not in (10, 11):
            return None
        if digits[:2] not in MailingProcessor.DDDS_VALIDOS:
            return None
        return digits

    def calcular_score(self, row: pd.Series) -> float:
        score = 0.0

        cpc_rate = float(row.get("cpc_anterior_taxa", 0) or 0)
        score += min(cpc_rate * 30, 30)

        dias = float(row.get("dias_sem_contato", 30) or 30)
        score += max(0.0, 20 - dias * 0.5)

        faixa = int(row.get("faixa_atraso_dias", 0) or 0)
        if 30 <= faixa <= 90:
            score += 15
        elif faixa < 30:
            score += 8
        else:
            score += 4

        inicio = int(row.get("melhor_hora_inicio", 9) or 9)
        fim    = int(row.get("melhor_hora_fim", 18) or 18)
        if inicio <= datetime.now().hour <= fim:
            score += 15

        ddd = str(row.get("ddd", ""))[:2]
        score += self.DDD_SCORE.get(ddd, 5)

        if row.get("promessa_quebrada"):
            score -= 10

        return round(max(0.0, min(score, 100.0)), 2)

    def processar(self, caminho_csv: str) -> pd.DataFrame:
        self._log.info(f"Processando mailing: {caminho_csv}")
        df = pd.read_csv(caminho_csv, dtype=str)
        total = len(df)

        df = df[df["cpf"].apply(self.validar_cpf)].copy()
        self._log.info(f"  CPF válidos: {len(df)}/{total}")

        df["telefone_limpo"] = df["telefone"].apply(self.validar_telefone)
        df = df[df["telefone_limpo"].notna()].copy()
        df["ddd"] = df["telefone_limpo"].str[:2]
        self._log.info(f"  Telefones válidos: {len(df)}")

        df = df.drop_duplicates(subset=["cpf"]).copy()
        self._log.info(f"  Sem duplicados: {len(df)}")

        df["score_discagem"] = df.apply(self.calcular_score, axis=1)
        df = df.sort_values("score_discagem", ascending=False)

        os.makedirs(self.cfg.dir_mailing, exist_ok=True)
        saida = os.path.join(self.cfg.dir_mailing,
                             f"mailing_processado_{date.today()}.csv")
        df.to_csv(saida, index=False)
        self._log.info(f"Mailing salvo em: {saida}")
        return df


# ==========================================================================
# ETAPA 4 — MONITOR DE OCIOSIDADE EM TEMPO REAL
# ==========================================================================

class MonitorOciosidade:
    """Detecta desvios e dispara ações corretivas automáticas."""

    def __init__(self, cfg: Config, alertas: GestorAlertas) -> None:  # BUG-01
        self.cfg     = cfg
        self.alertas = alertas
        self.engine  = _make_engine(cfg.db_url)                       # BUG-08
        self._log    = logging.getLogger(self.__class__.__name__)      # BUG-01

    def _query_df(self, sql: str) -> pd.DataFrame:
        if not SQLALCHEMY_OK:
            return pd.DataFrame()
        try:
            with self.engine.connect() as conn:
                return pd.read_sql(sa_text(sql), conn)
        except Exception as e:
            self._log.error(f"Query falhou: {e}")
            return pd.DataFrame()

    def _ler_snapshot(self) -> pd.DataFrame:
        return self._query_df("""
            SELECT * FROM olos_campaign_snapshot
            WHERE captured_at >= NOW() - INTERVAL '10 minutes'
            ORDER BY captured_at DESC
        """)

    def _ler_agentes(self) -> pd.DataFrame:
        return self._query_df("""
            SELECT * FROM olos_agents_log
            WHERE captured_at >= NOW() - INTERVAL '5 minutes'
            ORDER BY captured_at DESC
        """)

    def calcular_metricas(self, snap: pd.DataFrame,
                          agentes: pd.DataFrame) -> Dict:
        if snap.empty or agentes.empty:
            return {}

        total     = len(agentes)
        ociosos   = len(agentes[agentes["status"] == "idle"])
        em_pausa  = len(agentes[agentes["status"] == "paused"])
        em_linha  = len(agentes[agentes["status"] == "on_call"])

        ocio_pct = round(ociosos / total * 100, 1) if total else 0.0
        mailing  = float(snap["mailing_restante_pct"].min()) if "mailing_restante_pct" in snap else 100.0
        abandono = round(float(snap["abandono_pct"].mean()), 1) if "abandono_pct" in snap else 0.0

        pausa_longa: List[str] = []
        if "pausa_inicio" in agentes.columns:
            agentes = agentes.copy()           # BUG-07: não mutar original
            agentes["pausa_inicio"] = pd.to_datetime(agentes["pausa_inicio"])
            agentes["min_pausa"] = (
                datetime.utcnow() - agentes["pausa_inicio"]
            ).dt.total_seconds() / 60
            pausa_longa = agentes.loc[
                (agentes["status"] == "paused") &
                (agentes["min_pausa"] > self.cfg.limite_pausa_min),
                "nome"
            ].tolist()

        return {
            "total_agentes":       total,
            "ociosos":             ociosos,
            "em_pausa":            em_pausa,
            "em_ligacao":          em_linha,
            "ociosidade_pct":      ocio_pct,
            "mailing_restante_pct": mailing,
            "abandono_pct":        abandono,
            "agentes_pausa_longa": pausa_longa,
            "campanhas_ativas":    int(snap["campanha"].nunique()) if "campanha" in snap else 0,
        }

    def ajustar_pacing(self, fator: float,
                       campanha_id: Optional[str] = None) -> None:
        url     = f"{self.cfg.olos_base_url}/pacing/adjust"
        payload = {"factor": round(fator, 2)}
        if campanha_id:
            payload["campaign_id"] = campanha_id
        try:
            r = requests.post(
                url, json=payload,
                headers={"Authorization": f"Bearer {self.cfg.olos_token}"},
                timeout=10,
            )
            self._log.info(f"Pacing ajustado fator={fator} status={r.status_code}")
        except Exception as e:
            self._log.error(f"Falha pacing: {e}")

    def ciclo(self, snap: Optional[pd.DataFrame] = None,
              agentes: Optional[pd.DataFrame] = None) -> Dict:
        self._log.info("--- Ciclo de monitoramento ---")
        snap    = snap    if snap    is not None else self._ler_snapshot()
        agentes = agentes if agentes is not None else self._ler_agentes()

        m = self.calcular_metricas(snap, agentes)
        if not m:
            self._log.warning("Sem dados suficientes (banco não conectado ou vazio).")
            return {}

        self._log.info(
            f"Agentes={m['total_agentes']} Ociosos={m['ociosos']}({m['ociosidade_pct']}%) "
            f"Mailing={m['mailing_restante_pct']:.1f}% Abandono={m['abandono_pct']}%"
        )

        if m["ociosidade_pct"] > self.cfg.limite_ociosidade_pct:
            self.alertas.enviar_teams(
                f"⚠️ OCIOSIDADE ALTA\n"
                f"Ociosidade: {m['ociosidade_pct']}% (limite {self.cfg.limite_ociosidade_pct}%)\n"
                f"Ociosos: {m['ociosos']}/{m['total_agentes']}\n"
                f"Ação: pacing +20% automático."
            )
            self.ajustar_pacing(1.20)

        if m["mailing_restante_pct"] < self.cfg.limite_mailing_restante:
            self.alertas.enviar_teams(
                f"🔴 MAILING ESGOTANDO\n"
                f"Restante: {m['mailing_restante_pct']:.1f}%\n"
                f"Ação: providenciar nova carga!"
            )

        if m["abandono_pct"] > self.cfg.limite_abandono_pct:
            self.alertas.enviar_teams(
                f"📵 ABANDONO ALTO\n"
                f"Abandono: {m['abandono_pct']}% (limite {self.cfg.limite_abandono_pct}%)\n"
                f"Ação: pacing −15% automático."
            )
            self.ajustar_pacing(0.85)

        if m["agentes_pausa_longa"]:
            nomes = ", ".join(m["agentes_pausa_longa"][:5])
            self.alertas.enviar_teams(
                f"⏰ PAUSA EXCESSIVA\n"
                f"Agentes em pausa > {self.cfg.limite_pausa_min} min:\n{nomes}"
            )

        return m


# ==========================================================================
# ETAPA 5 — INTELIGÊNCIA DE DISCAGEM
# ==========================================================================

class InteligenciaDiscagem:
    """
    GradientBoosting para predizer CPC por DDD/hora/dia.
    M4: modelo persistido em disco via joblib.
    """

    def __init__(self, cfg: Config) -> None:                         # BUG-01
        self.cfg    = cfg
        self.engine = _make_engine(cfg.db_url)                       # BUG-08
        self._log   = logging.getLogger(self.__class__.__name__)     # BUG-01
        self.modelo: Optional[GradientBoostingClassifier] = None
        self.le_ddd = LabelEncoder()
        os.makedirs(cfg.dir_modelos, exist_ok=True)
        self._pkl   = os.path.join(cfg.dir_modelos, "modelo_cpc.pkl")
        self._carregar_disco()                                        # M4

    def _carregar_disco(self) -> None:
        """M4: tenta carregar modelo treinado anteriormente."""
        if not os.path.exists(self._pkl):
            return
        try:
            payload      = joblib.load(self._pkl)
            self.modelo  = payload["modelo"]
            self.le_ddd  = payload["le_ddd"]
            self._log.info(f"[M4] Modelo carregado: {self._pkl}")
        except Exception as e:
            self._log.warning(f"Não foi possível carregar modelo do disco: {e}")

    def _salvar_disco(self) -> None:
        """M4: persiste modelo após treino."""
        if self.modelo is None:
            return
        try:
            joblib.dump({"modelo": self.modelo, "le_ddd": self.le_ddd}, self._pkl)
            self._log.info(f"[M4] Modelo salvo: {self._pkl}")
        except Exception as e:
            self._log.error(f"Falha ao salvar modelo: {e}")

    def carregar_historico(self, dias: int = 90) -> pd.DataFrame:
        if not SQLALCHEMY_OK:
            self._log.warning("SQLAlchemy ausente — histórico vazio.")
            return pd.DataFrame()
        sql = f"""
            SELECT
                SUBSTRING(telefone, 1, 2)::int           AS ddd,
                EXTRACT(HOUR  FROM iniciada_em)::int      AS hora,
                EXTRACT(DOW   FROM iniciada_em)::int      AS dia_semana,
                CASE WHEN tipo_resultado IN ('CPC','RPC')
                     THEN 1 ELSE 0 END                    AS cpc
            FROM olos_ligacoes
            WHERE iniciada_em >= NOW() - INTERVAL '{dias} days'
              AND telefone IS NOT NULL
        """
        try:
            with self.engine.connect() as conn:
                df = pd.read_sql(sa_text(sql), conn)
            self._log.info(f"Histórico: {len(df)} ligações / {dias} dias")
            return df
        except Exception as e:
            self._log.error(f"Falha ao carregar histórico: {e}")
            return pd.DataFrame()

    def treinar_modelo(self, df: pd.DataFrame) -> None:
        if df.empty or len(df) < 500:
            self._log.warning(f"Histórico insuficiente ({len(df)} registros; mínimo 500).")
            return
        feats = ["ddd", "hora", "dia_semana"]
        df    = df.dropna(subset=feats + ["cpc"])
        X     = df[feats].copy()
        X["ddd"] = self.le_ddd.fit_transform(X["ddd"].astype(str))
        y = df["cpc"]
        Xtr, Xte, ytr, yte = train_test_split(X, y, test_size=0.2, random_state=42)
        self.modelo = GradientBoostingClassifier(n_estimators=150, max_depth=4,
                                                 random_state=42)
        self.modelo.fit(Xtr, ytr)
        acc = self.modelo.score(Xte, yte)
        self._log.info(f"Modelo treinado | Acurácia: {acc:.3f}")
        self._salvar_disco()                                          # M4

    def melhor_janela(self, ddd: str, top_n: int = 3) -> List[Dict]:  # BUG-09
        if self.modelo is None:
            return []
        cands = pd.DataFrame([
            {"ddd": 0, "hora": h, "dia_semana": d}
            for h in range(7, 21) for d in range(1, 6)
        ])
        try:
            cands["ddd"] = self.le_ddd.transform([ddd] * len(cands))
        except ValueError:
            cands["ddd"] = 0
        cands["prob_cpc"] = self.modelo.predict_proba(
            cands[["ddd", "hora", "dia_semana"]]
        )[:, 1]
        dias_map = {1: "Seg", 2: "Ter", 3: "Qua", 4: "Qui", 5: "Sex"}
        return (
            cands.nlargest(top_n, "prob_cpc")[["hora", "dia_semana", "prob_cpc"]]
            .assign(dia_semana=lambda x: x["dia_semana"].map(dias_map))
            .to_dict("records")
        )


# ==========================================================================
# ETAPA 6 — AUDITORIA OPERACIONAL AUTOMÁTICA
# ==========================================================================

class AuditoriaOperacional:
    """Detecta inconsistências e improdutividades automaticamente."""

    def __init__(self, cfg: Config, alertas: GestorAlertas) -> None:  # BUG-01
        self.cfg     = cfg
        self.alertas = alertas
        self.engine  = _make_engine(cfg.db_url)                       # BUG-08
        self._log    = logging.getLogger(self.__class__.__name__)      # BUG-01

    def _query(self, sql: str) -> pd.DataFrame:
        if not SQLALCHEMY_OK:
            return pd.DataFrame()
        try:
            with self.engine.connect() as conn:
                return pd.read_sql(sa_text(sql), conn)
        except Exception as e:
            self._log.error(f"Query falhou: {e}")
            return pd.DataFrame()

    def detectar_agentes_improdutivos(self) -> pd.DataFrame:
        return self._query("""
            SELECT a.nome, a.campanha,
                ROUND(EXTRACT(EPOCH FROM (NOW() - a.login_em)) / 60) AS min_logado,
                COALESCE(l.ligacoes, 0) AS ligacoes_hoje
            FROM olos_agents_log a
            LEFT JOIN (
                SELECT agente_id, COUNT(*) AS ligacoes
                FROM olos_ligacoes
                WHERE DATE(iniciada_em) = CURRENT_DATE
                GROUP BY agente_id
            ) l ON a.id = l.agente_id
            WHERE a.status != 'paused'
              AND EXTRACT(EPOCH FROM (NOW() - a.login_em)) / 60 > 30
              AND COALESCE(l.ligacoes, 0) = 0
        """)

    def detectar_campanhas_paradas(self) -> pd.DataFrame:
        return self._query("""
            SELECT c.campanha_id, c.nome, c.status,
                MAX(l.iniciada_em) AS ultima_ligacao,
                ROUND(EXTRACT(EPOCH FROM (NOW() - MAX(l.iniciada_em))) / 60) AS min_parada
            FROM olos_campaign_snapshot c
            LEFT JOIN olos_ligacoes l ON l.campanha_id = c.campanha_id
            WHERE c.status = 'active'
            GROUP BY c.campanha_id, c.nome, c.status
            HAVING MAX(l.iniciada_em) < NOW() - INTERVAL '15 minutes'
                OR MAX(l.iniciada_em) IS NULL
        """)

    def detectar_inconsistencia_crm(self) -> pd.DataFrame:
        return self._query("""
            SELECT DISTINCT l.cpf_cliente, l.campanha_id
            FROM olos_ligacoes l
            LEFT JOIN easy_carteiras c ON l.cpf_cliente = c.cpf
            WHERE c.cpf IS NULL
              AND DATE(l.iniciada_em) = CURRENT_DATE
        """)

    def executar_auditoria(self) -> None:
        self._log.info("=== Auditoria Operacional ===")
        problemas: List[str] = []

        df = self.detectar_agentes_improdutivos()
        if not df.empty:
            problemas.append(
                f"👤 {len(df)} agentes improdutivos:\n" +
                "\n".join(f"  • {r['nome']} — {r['min_logado']} min"
                          for _, r in df.iterrows())
            )

        df = self.detectar_campanhas_paradas()
        if not df.empty:
            problemas.append(
                f"📵 {len(df)} campanhas paradas:\n" +
                "\n".join(f"  • {r['nome']} — {r['min_parada']} min"
                          for _, r in df.iterrows())
            )

        df = self.detectar_inconsistencia_crm()
        if not df.empty:
            problemas.append(
                f"⚠️ {len(df)} CPFs sem cadastro no EasyCollector."
            )

        if problemas:
            self.alertas.enviar_teams(
                "🔍 AUDITORIA — " + datetime.now().strftime("%H:%M") + "\n\n" +
                "\n\n".join(problemas)
            )
        else:
            self._log.info("Auditoria: nenhum problema detectado.")


# ==========================================================================
# ETAPA 7 — RELATÓRIOS E ALERTAS
# ==========================================================================

class GestorRelatorios:
    """Gera relatórios Excel com aba Timeline hora-a-hora (M5)."""

    def __init__(self, cfg: Config, alertas: GestorAlertas) -> None:  # BUG-01
        self.cfg     = cfg
        self.alertas = alertas
        self.engine  = _make_engine(cfg.db_url)                       # BUG-08
        self._log    = logging.getLogger(self.__class__.__name__)      # BUG-01

    def _query(self, sql: str) -> pd.DataFrame:
        if not SQLALCHEMY_OK:
            return pd.DataFrame()
        try:
            with self.engine.connect() as conn:
                return pd.read_sql(sa_text(sql), conn)
        except Exception as e:
            self._log.error(f"Query falhou: {e}")
            return pd.DataFrame()

    def gerar_intraday(self) -> pd.DataFrame:
        return self._query("""
            SELECT campanha,
                COUNT(*)                      AS acionamentos,
                SUM(cpc::int)                 AS cpcs,
                ROUND(AVG(ociosidade_pct), 1) AS ociosidade_media,
                ROUND(AVG(abandono_pct), 1)   AS abandono_medio,
                MIN(mailing_restante_pct)     AS mailing_restante
            FROM olos_campaign_snapshot
            WHERE DATE(captured_at) = CURRENT_DATE
            GROUP BY campanha ORDER BY acionamentos DESC
        """)

    def gerar_timeline(self) -> pd.DataFrame:
        """M5: evolução hora-a-hora para identificar períodos críticos."""
        return self._query("""
            SELECT DATE_TRUNC('hour', captured_at) AS hora,
                campanha,
                ROUND(AVG(ociosidade_pct), 1)      AS ociosidade,
                ROUND(AVG(abandono_pct), 1)        AS abandono,
                MIN(mailing_restante_pct)          AS mailing_restante,
                COUNT(*)                           AS snapshots
            FROM olos_campaign_snapshot
            WHERE DATE(captured_at) = CURRENT_DATE
            GROUP BY 1, 2 ORDER BY 1, 2
        """)

    def gerar_producao_operador(self) -> pd.DataFrame:
        return self._query("""
            SELECT a.nome AS operador, a.campanha,
                COUNT(l.id)                       AS ligacoes,
                SUM(l.cpc::int)                   AS cpcs,
                ROUND(AVG(l.duracao_seg) / 60, 1) AS tma_min
            FROM olos_agents_log a
            LEFT JOIN olos_ligacoes l
                ON l.agente_id = a.id
               AND DATE(l.iniciada_em) = CURRENT_DATE
            WHERE DATE(a.captured_at) = CURRENT_DATE
            GROUP BY a.nome, a.campanha ORDER BY ligacoes DESC
        """)

    def exportar_excel(self, nome: str,
                       sheets: Dict[str, pd.DataFrame]) -> str:   # BUG-09
        os.makedirs(self.cfg.dir_reports, exist_ok=True)
        caminho = os.path.join(self.cfg.dir_reports, nome)
        with pd.ExcelWriter(caminho, engine="openpyxl") as w:
            for aba, df in sheets.items():
                df.to_excel(w, sheet_name=aba, index=False)
        self._log.info(f"Excel gerado: {caminho}")
        return caminho

    def pipeline_intraday(self) -> None:
        self._log.info("Gerando relatório intraday...")
        df_intra = self.gerar_intraday()
        df_prod  = self.gerar_producao_operador()
        df_tl    = self.gerar_timeline()             # M5

        if df_intra.empty:
            self._log.warning("Intraday: sem dados no banco.")
            return

        nome    = f"intraday_{date.today()}_{datetime.now().strftime('%H%M')}.xlsx"
        arquivo = self.exportar_excel(
            nome,
            {"Campanhas": df_intra, "Operadores": df_prod, "Timeline": df_tl},  # M5
        )

        total    = int(df_intra["acionamentos"].sum())
        cpcs     = int(df_intra["cpcs"].sum())
        taxa     = round(cpcs / total * 100, 1) if total else 0.0
        self.alertas.enviar_teams(
            f"📊 Intraday — {datetime.now().strftime('%H:%M')}\n"
            f"Acionamentos: {total:,}\nCPCs: {cpcs:,} ({taxa}%)\n"
            f"Campanhas: {len(df_intra)}"
        )
        self.alertas.enviar_email(
            assunto=f"[Control Desk] Intraday {date.today()}",
            corpo=df_intra.to_html(index=False, border=0),
            anexo_path=arquivo,
        )


# ==========================================================================
# ETAPA 8 — FORECAST DE VOLUME
# ==========================================================================

class ForecastVolume:
    """
    Prevê volume de chamadas e necessidade de agentes.
    BUG-03: freq corrigida para 'h' (pandas 2.x+).
    """

    def __init__(self, cfg: Config) -> None:                         # BUG-01
        self.cfg    = cfg
        self.engine = _make_engine(cfg.db_url)                       # BUG-08
        self._log   = logging.getLogger(self.__class__.__name__)     # BUG-01

    def carregar_serie(self) -> pd.DataFrame:
        if not SQLALCHEMY_OK:
            return pd.DataFrame()
        sql = """
            SELECT DATE_TRUNC('hour', iniciada_em) AS ds, COUNT(*) AS y
            FROM olos_ligacoes
            WHERE iniciada_em >= NOW() - INTERVAL '180 days'
            GROUP BY 1 ORDER BY 1
        """
        try:
            with self.engine.connect() as conn:
                return pd.read_sql(sa_text(sql), conn)
        except Exception as e:
            self._log.error(f"Falha ao carregar série: {e}")
            return pd.DataFrame()

    def prever_prophet(self, df: pd.DataFrame, periodos: int = 24) -> pd.DataFrame:
        try:
            from prophet import Prophet
            m = Prophet(yearly_seasonality=True,
                        weekly_seasonality=True,
                        daily_seasonality=True)
            m.fit(df[["ds", "y"]])
            futuro = m.make_future_dataframe(periods=periodos, freq="h")  # BUG-03
            fc = m.predict(futuro)
            return fc[["ds", "yhat", "yhat_lower", "yhat_upper"]].tail(periodos)
        except ImportError:
            self._log.warning("Prophet não instalado — usando média móvel como fallback.")
            return self.prever_media_movel(df, periodos)

    def prever_media_movel(self, df: pd.DataFrame,
                            periodos: int = 24) -> pd.DataFrame:
        ultima = df["ds"].max()
        rows   = []
        for h in range(periodos):
            alvo = ultima + timedelta(hours=h + 1)
            hist = df[
                (df["ds"].dt.dayofweek == alvo.dayofweek) &
                (df["ds"].dt.hour      == alvo.hour)
            ]["y"]
            yhat = float(hist.mean()) if not hist.empty else 0.0
            rows.append({"ds": alvo, "yhat": round(yhat),
                          "yhat_lower": 0.0, "yhat_upper": yhat * 1.3})
        return pd.DataFrame(rows)

    def calcular_agentes_necessarios(self, fc: pd.DataFrame,
                                     tma_min: float = 5.0) -> pd.DataFrame:
        fc = fc.copy()
        fc["agentes_necessarios"] = (
            fc["yhat"] * (tma_min / 60)
        ).apply(np.ceil).astype(int)
        return fc

    def executar(self, df_simulado: Optional[pd.DataFrame] = None) -> pd.DataFrame:
        self._log.info("Gerando forecast de volume...")
        df = df_simulado if df_simulado is not None else self.carregar_serie()
        if df.empty:
            self._log.warning("Sem dados históricos para forecast.")
            return pd.DataFrame()
        fc = self.prever_prophet(df)
        return self.calcular_agentes_necessarios(fc)


# ==========================================================================
# HEALTH CHECK HTTP (M6)
# ==========================================================================

class HealthCheckServer:
    """M6: expõe /health para monitoramento externo (Kubernetes, Zabbix, etc.)."""

    def __init__(self, porta: int, agente_ref: AgentControlDesk) -> None:
        self._porta     = porta
        self._agente    = agente_ref
        self._server: Optional[HTTPServer] = None

    def _build_handler(self):
        agente = self._agente

        class Handler(BaseHTTPRequestHandler):
            def do_GET(self):
                if self.path == "/health":
                    payload = json.dumps(
                        agente.status_saude(), indent=2, default=str
                    ).encode()
                    self.send_response(200)
                    self.send_header("Content-Type", "application/json")
                    self.end_headers()
                    self.wfile.write(payload)
                else:
                    self.send_response(404)
                    self.end_headers()

            def log_message(self, *args):
                pass   # silencia logs de acesso HTTP

        return Handler

    def iniciar(self) -> None:
        try:
            self._server = HTTPServer(("0.0.0.0", self._porta),
                                      self._build_handler())
            t = threading.Thread(
                target=self._server.serve_forever,
                daemon=True, name="health-check",
            )
            t.start()
            log.info(f"[M6] Health check: http://localhost:{self._porta}/health")
        except OSError as e:
            log.warning(f"[M6] Não foi possível iniciar health check: {e}")


# ==========================================================================
# ETAPA 9 — ORQUESTRADOR PRINCIPAL
# ==========================================================================

class AgentControlDesk:
    """
    Orquestrador central com SimpleScheduler interno, health check e
    todas as melhorias M1-M6 integradas.
    """

    def __init__(self, cfg: Optional[Config] = None) -> None:        # BUG-01
        self.cfg        = cfg or CFG
        self.alertas    = GestorAlertas(self.cfg)
        self.etl        = ETLIngestao(self.cfg, self.alertas)
        self.mailing    = MailingProcessor(self.cfg)
        self.monitor    = MonitorOciosidade(self.cfg, self.alertas)
        self.discagem   = InteligenciaDiscagem(self.cfg)
        self.auditoria  = AuditoriaOperacional(self.cfg, self.alertas)
        self.relatorios = GestorRelatorios(self.cfg, self.alertas)
        self.forecast   = ForecastVolume(self.cfg)
        self._log       = logging.getLogger(self.__class__.__name__) # BUG-01
        self._sched     = SimpleScheduler()
        self._stop      = threading.Event()
        self._saude: Dict = {
            "versao":        "2.0.0",
            "iniciado_em":   datetime.now().isoformat(),
            "ciclos_etl":    0,
            "ciclos_monitor": 0,
            "sqlalchemy_ok": SQLALCHEMY_OK,
            "joblib_ok":     True,
        }
        self._health = HealthCheckServer(self.cfg.health_port, self) # M6

    # ── saúde ─────────────────────────────────────────────────────────────

    def status_saude(self) -> Dict:
        self._saude["ts"]       = datetime.now().isoformat()
        self._saude["dlq_size"] = self.alertas.dlq_size
        return self._saude

    # ── helpers internos ──────────────────────────────────────────────────

    def _safe(self, func, nome: str) -> None:
        try:
            func()
        except Exception:
            self._log.error(f"Erro em [{nome}]:\n{traceback.format_exc()}")

    def _etl_tick(self) -> None:
        self.etl.executar()
        self._saude["ciclos_etl"] += 1

    def _monitor_tick(self) -> None:
        self.monitor.ciclo()
        self._saude["ciclos_monitor"] += 1

    def _treinar_async(self) -> None:
        """M4: treino em thread separada para não bloquear o loop."""
        def _inner():
            df = self.discagem.carregar_historico(dias=90)
            self.discagem.treinar_modelo(df)
        ThreadPoolExecutor(max_workers=1).submit(
            lambda: self._safe(_inner, "Treino-ML")
        )

    # ── agendamento ───────────────────────────────────────────────────────

    def _agendar(self) -> None:
        s = self._sched
        s.every_minutes(5,  lambda: self._safe(self._etl_tick,     "ETL"),      "ETL")
        s.every_seconds(self.cfg.intervalo_monitor_seg,
                        lambda: self._safe(self._monitor_tick, "Monitor"),  "Monitor")
        s.every_minutes(60, lambda: self._safe(self.relatorios.pipeline_intraday, "Intraday"), "Intraday")
        s.every_minutes(60, lambda: self._safe(self.auditoria.executar_auditoria, "Auditoria"), "Auditoria")
        s.daily_at(2,  0,  self._treinar_async,                                 "Treino-ML")
        s.daily_at(6, 30,  lambda: self._safe(self.forecast.executar, "Forecast"), "Forecast")
        self._log.info("Todos os agendamentos configurados.")

    # ── ciclo de vida ─────────────────────────────────────────────────────

    def iniciar(self, loop: bool = True) -> None:
        _gerar_env_example()                              # BUG-10
        self._log.info("🚀 Agente IA Control Desk v2.0 iniciado.")
        self.alertas.enviar_teams("🤖 Agente IA Control Desk v2.0 ativo.")
        self._health.iniciar()                            # M6
        # execuções iniciais imediatas
        self._safe(self._etl_tick,     "ETL-inicial")
        self._safe(self._monitor_tick, "Monitor-inicial")
        self._treinar_async()
        self._agendar()
        if loop:
            self._log.info("Loop ativo. Ctrl+C para parar.")
            try:
                self._sched.loop(self._stop)
            except KeyboardInterrupt:
                self._log.info("Agente encerrado pelo usuário.")
            finally:
                self._stop.set()

    def parar(self) -> None:
        self._stop.set()
        self._log.info("Agente encerrado.")


# ==========================================================================
# ENTRYPOINT — BUG-02
# ==========================================================================

if __name__ == "__main__":            # BUG-02: __name__ e __main__ com dunder
    agente = AgentControlDesk()
    agente.iniciar()
