from __future__ import annotations

import os

from dotenv import load_dotenv

load_dotenv()


class Config:
    """Centraliza todas as configurações via variáveis de ambiente ou .env."""

    def __init__(self) -> None:
        # ── Banco de dados ───────────────────────────────────
        self.POSTGRES_HOST     = os.getenv("POSTGRES_HOST", "localhost")
        self.POSTGRES_PORT     = os.getenv("POSTGRES_PORT", "5432")
        self.POSTGRES_DB       = os.getenv("POSTGRES_DB", "control_desk")
        self.POSTGRES_USER     = os.getenv("POSTGRES_USER", "postgres")
        self.POSTGRES_PASSWORD = os.getenv("POSTGRES_PASSWORD", "postgres")

        # ── Olos (discador) ──────────────────────────────────
        self.OLOS_BASE_URL = os.getenv("OLOS_BASE_URL", "https://olos.suaempresa.com/api/v2")
        self.OLOS_TOKEN    = os.getenv("OLOS_TOKEN", "")

        # ── EasyCollector (CRM de cobrança) ───────────────────
        self.EASY_BASE_URL = os.getenv("EASY_BASE_URL", "https://easycollector.suaempresa.com/api")
        self.EASY_TOKEN    = os.getenv("EASY_TOKEN", "")

        # ── Alertas ───────────────────────────────────────────
        self.TEAMS_WEBHOOK = os.getenv("TEAMS_WEBHOOK", "")
        self.EMAIL_SMTP    = os.getenv("EMAIL_SMTP", "")
        self.EMAIL_PORTA   = int(os.getenv("EMAIL_PORTA", "587"))
        self.EMAIL_USER    = os.getenv("EMAIL_USER", "")
        self.EMAIL_SENHA   = os.getenv("EMAIL_SENHA", "")
        self.EMAIL_DESTINOS = os.getenv("EMAIL_DESTINOS", "")

        # ── Analisador de ligações ALO / NÃO ALO (IA) ────────
        self.ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY", "")
        self.ANTHROPIC_MODEL   = os.getenv("ANTHROPIC_MODEL", "claude-opus-4-8")
        self.ALO_USAR_IA       = os.getenv("ALO_USAR_IA", "true").lower() == "true"

        # ── JWT (API) ─────────────────────────────────────────
        self.JWT_SECRET_KEY     = os.getenv("JWT_SECRET_KEY", "TROQUE_EM_PRODUCAO")
        self.JWT_ALGORITHM      = os.getenv("JWT_ALGORITHM", "HS256")
        self.JWT_EXPIRE_MINUTES = int(os.getenv("JWT_EXPIRE_MINUTES", "480"))

        # ── Limites operacionais ──────────────────────────────
        self.LIMITE_OCIOSIDADE_PCT   = float(os.getenv("LIMITE_OCIOSIDADE_PCT", "15.0"))
        self.LIMITE_ABANDONO_PCT     = float(os.getenv("LIMITE_ABANDONO_PCT", "8.0"))
        self.LIMITE_MAILING_RESTANTE = float(os.getenv("LIMITE_MAILING_RESTANTE_PCT", "5.0"))
        self.LIMITE_PAUSA_MIN        = int(os.getenv("LIMITE_PAUSA_MIN", "20"))
        self.INTERVALO_MONITOR_SEG   = int(os.getenv("INTERVALO_MONITOR_SEG", "120"))
        self.THROTTLE_ALERTAS_SEG    = int(os.getenv("THROTTLE_ALERTAS_SEG", "300"))

        # ── Guardrails de pacing ──────────────────────────────
        self.PACING_HORA_INICIO_GLOBAL = os.getenv("PACING_HORA_INICIO_GLOBAL", "08:00")
        self.PACING_HORA_FIM_GLOBAL    = os.getenv("PACING_HORA_FIM_GLOBAL", "21:00")
        self.PACING_HORA_FIM_SABADO    = os.getenv("PACING_HORA_FIM_SABADO", "16:00")
        self.PACING_MAX_GLOBAL         = float(os.getenv("PACING_MAX_GLOBAL", "8.0"))
        self.PACING_MIN_GLOBAL         = float(os.getenv("PACING_MIN_GLOBAL", "1.0"))
        self.PAUSAR_EM_FERIADOS        = os.getenv("PAUSAR_EM_FERIADOS", "true").lower() == "true"

        # ── Circuit breaker (APIs externas) ───────────────────
        self.CB_MAX_FALHAS = int(os.getenv("CB_MAX_FALHAS", "3"))
        self.CB_PAUSA_MIN  = int(os.getenv("CB_PAUSA_MIN", "10"))

        # ── Cache de snapshot ──────────────────────────────────
        self.CACHE_TTL_SEG = int(os.getenv("CACHE_TTL_SEG", "90"))

        # ── Diretórios de saída ────────────────────────────────
        self.DIR_MAILING = os.getenv("DIR_MAILING", "./data/mailing")
        self.DIR_REPORTS = os.getenv("DIR_REPORTS", "./data/reports")
        self.DIR_MODELOS = os.getenv("DIR_MODELOS", "./models")

        # ── Health check (modo standalone, sem FastAPI) ───────
        self.HEALTH_PORT = int(os.getenv("HEALTH_PORT", "8080"))

        # ── Ambiente ────────────────────────────────────────
        self.AMBIENTE  = os.getenv("AMBIENTE", "development")
        self.LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")

    @property
    def DATABASE_URL(self) -> str:
        return (
            f"postgresql://{self.POSTGRES_USER}:{self.POSTGRES_PASSWORD}"
            f"@{self.POSTGRES_HOST}:{self.POSTGRES_PORT}/{self.POSTGRES_DB}"
        )

    @property
    def EMAIL_DESTINOS_LIST(self) -> list[str]:
        return [e.strip() for e in self.EMAIL_DESTINOS.split(",") if e.strip()]


CFG = Config()


def gerar_env_example() -> None:
    """Cria .env.example de referência na raiz do projeto, se não existir."""
    if os.path.exists(".env.example"):
        return
    linhas = [
        "POSTGRES_HOST=localhost",
        "POSTGRES_PORT=5432",
        "POSTGRES_DB=control_desk",
        "POSTGRES_USER=postgres",
        "POSTGRES_PASSWORD=",
        "",
        "OLOS_BASE_URL=https://olos.suaempresa.com/api/v2",
        "OLOS_TOKEN=",
        "EASY_BASE_URL=https://easycollector.suaempresa.com/api",
        "EASY_TOKEN=",
        "",
        "TEAMS_WEBHOOK=",
        "EMAIL_SMTP=",
        "EMAIL_PORTA=587",
        "EMAIL_USER=",
        "EMAIL_SENHA=",
        "EMAIL_DESTINOS=supervisao@empresa.com,gerencia@empresa.com",
        "",
        "ANTHROPIC_API_KEY=",
        "ANTHROPIC_MODEL=claude-opus-4-8",
        "ALO_USAR_IA=true",
        "",
        "JWT_SECRET_KEY=troque-por-uma-chave-secreta-forte",
        "JWT_ALGORITHM=HS256",
        "JWT_EXPIRE_MINUTES=480",
        "",
        "LIMITE_OCIOSIDADE_PCT=15.0",
        "LIMITE_ABANDONO_PCT=8.0",
        "LIMITE_MAILING_RESTANTE_PCT=5.0",
        "LIMITE_PAUSA_MIN=20",
        "INTERVALO_MONITOR_SEG=120",
        "THROTTLE_ALERTAS_SEG=300",
        "",
        "PACING_HORA_INICIO_GLOBAL=08:00",
        "PACING_HORA_FIM_GLOBAL=21:00",
        "PACING_HORA_FIM_SABADO=16:00",
        "PACING_MAX_GLOBAL=8.0",
        "PACING_MIN_GLOBAL=1.0",
        "PAUSAR_EM_FERIADOS=true",
        "",
        "CB_MAX_FALHAS=3",
        "CB_PAUSA_MIN=10",
        "CACHE_TTL_SEG=90",
        "HEALTH_PORT=8080",
        "",
        "AMBIENTE=development",
        "LOG_LEVEL=INFO",
    ]
    with open(".env.example", "w", encoding="utf-8") as f:
        f.write("\n".join(linhas) + "\n")
