"""Configuração central (Config, CFG).

Camada base: lê variáveis de ambiente (e .env). Não importa outras camadas —
usa `logging.getLogger` diretamente para evitar dependência circular com o
setup de logging.
"""
from __future__ import annotations

import logging
import os

log = logging.getLogger("ControlDesk")


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
        # "plain" (padrão, compatível) ou "json" (logs estruturados Enterprise).
        self.LOG_FORMAT = os.getenv("LOG_FORMAT", "plain").lower()

        # ── Resiliência de jobs (Fase 2) ────────────────────
        # Timeout generoso por padrão (protege contra jobs presos, sem afetar
        # jobs normais). Retry desligado por padrão (0) porque nem todo job é
        # idempotente — habilite por job só quando for seguro.
        self.JOB_TIMEOUT_SEG   = int(os.getenv("JOB_TIMEOUT_SEG",   "900"))
        self.JOB_MAX_RETRIES   = int(os.getenv("JOB_MAX_RETRIES",   "0"))
        self.RETRY_BASE_SEG    = float(os.getenv("RETRY_BASE_SEG",  "1.0"))
        self.RETRY_MAX_SEG     = float(os.getenv("RETRY_MAX_SEG",   "30.0"))
        self.CB_FAIL_THRESHOLD = int(os.getenv("CB_FAIL_THRESHOLD", "5"))
        self.CB_RESET_SEG      = int(os.getenv("CB_RESET_SEG",      "60"))

        # ── ETL Enterprise (Melhoria 1) ─────────────────────
        # UPSERT idempotente para tabelas com chave natural (cai para append
        # se o índice único não existir). Retenção de snapshots desligada (0).
        self.ETL_UPSERT        = os.getenv("ETL_UPSERT", "true").lower() == "true"
        self.ETL_RETENCAO_DIAS = int(os.getenv("ETL_RETENCAO_DIAS", "0"))

        # ── Cache & Filas (Fase 3) ──────────────────────────
        # Sem REDIS_URL/CELERY_BROKER_URL a app usa fallback em memória /
        # fila in-process — funciona sem infra externa.
        self.REDIS_URL             = os.getenv("REDIS_URL", "")
        self.CACHE_TTL_SEG         = int(os.getenv("CACHE_TTL_SEG", "30"))
        self.CELERY_BROKER_URL     = os.getenv("CELERY_BROKER_URL", "")
        self.CELERY_RESULT_BACKEND = os.getenv("CELERY_RESULT_BACKEND", "")
        self.QUEUE_WORKERS         = int(os.getenv("QUEUE_WORKERS", "2"))

        # ── Banco: pool, timeout, retry, read replica (Fase 4) ──
        self.POSTGRES_POOL_SIZE      = int(os.getenv("POSTGRES_POOL_SIZE", "5"))
        self.POSTGRES_MAX_OVERFLOW   = int(os.getenv("POSTGRES_MAX_OVERFLOW", "10"))
        self.DB_STATEMENT_TIMEOUT_MS = int(os.getenv("DB_STATEMENT_TIMEOUT_MS", "0"))  # 0 = sem limite
        self.DB_READ_RETRY           = int(os.getenv("DB_READ_RETRY", "2"))
        self.DATABASE_REPLICA_URL    = os.getenv("DATABASE_REPLICA_URL", "")  # vazio = usa a primária
        self.ETL_PARALELO            = os.getenv("ETL_PARALELO", "true").lower() == "true"

        # ── IA (Fase 5) ─────────────────────────────────────
        self.IA_MODELO_DIR   = os.getenv("IA_MODELO_DIR", "models")
        self.IA_MIN_AMOSTRAS = int(os.getenv("IA_MIN_AMOSTRAS", "200"))

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
