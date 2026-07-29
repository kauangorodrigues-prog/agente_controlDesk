"""Configuração central da aplicação.

Todas as configurações são carregadas de variáveis de ambiente (ou de um
arquivo .env), com valores padrão seguros para desenvolvimento local.
"""
from __future__ import annotations

import os
from functools import lru_cache
from typing import List

try:  # carrega .env se disponível
    from dotenv import load_dotenv

    load_dotenv()
except Exception:  # pragma: no cover
    pass


class Settings:
    """Configurações da aplicação (12-factor / env driven)."""

    def __init__(self) -> None:
        # ── Identidade da aplicação ─────────────────────────────
        self.APP_NAME: str = os.getenv("APP_NAME", "ControlDesk Cobranças SaaS")
        self.APP_ENV: str = os.getenv("APP_ENV", "development")
        self.APP_VERSION: str = os.getenv("APP_VERSION", "1.0.0")
        self.DEBUG: bool = os.getenv("DEBUG", "true").lower() == "true"

        # ── Banco de Dados ──────────────────────────────────────
        # Padrão: SQLite (zero-config, roda em qualquer lugar).
        # Produção: defina DATABASE_URL para PostgreSQL.
        #   ex: postgresql+psycopg://user:pass@host:5432/cobranca
        self.DATABASE_URL: str = os.getenv(
            "DATABASE_URL", "sqlite:///./controldesk.db"
        )

        # ── Segurança / JWT ─────────────────────────────────────
        self.JWT_SECRET_KEY: str = os.getenv(
            "JWT_SECRET_KEY", "dev-secret-key-TROQUE-EM-PRODUCAO"
        )
        self.JWT_ALGORITHM: str = os.getenv("JWT_ALGORITHM", "HS256")
        self.ACCESS_TOKEN_EXPIRE_MINUTES: int = int(
            os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", "480")
        )
        # Custo do hashing bcrypt (rounds). 12 é um bom padrão de produção.
        self.BCRYPT_ROUNDS: int = int(os.getenv("BCRYPT_ROUNDS", "12"))

        # ── Criptografia de dados em repouso (LGPD art. 46) ────
        # Chave para cifrar PII sensível (CPF/CNPJ) no banco.
        self.DATA_ENCRYPTION_KEY: str = os.getenv(
            "DATA_ENCRYPTION_KEY", "dev-data-encryption-key-TROQUE-EM-PRODUCAO"
        )
        # Chave HMAC para índice cego (busca por documento sem expor o valor).
        self.DATA_INDEX_KEY: str = os.getenv(
            "DATA_INDEX_KEY", "dev-blind-index-key-TROQUE-EM-PRODUCAO"
        )

        # ── Proteção de autenticação (brute-force) ─────────────
        self.LOGIN_MAX_ATTEMPTS: int = int(os.getenv("LOGIN_MAX_ATTEMPTS", "5"))
        self.LOGIN_LOCKOUT_SECONDS: int = int(os.getenv("LOGIN_LOCKOUT_SECONDS", "300"))

        # ── Notificações (SMTP) ────────────────────────────────
        # Sem SMTP_HOST, a régua opera em modo simulado (dry-run).
        self.SMTP_HOST: str = os.getenv("SMTP_HOST", "")
        self.SMTP_PORT: int = int(os.getenv("SMTP_PORT", "587"))
        self.SMTP_USER: str = os.getenv("SMTP_USER", "")
        self.SMTP_PASSWORD: str = os.getenv("SMTP_PASSWORD", "")
        self.SMTP_USE_TLS: bool = os.getenv("SMTP_USE_TLS", "true").lower() == "true"
        self.SMTP_FROM: str = os.getenv(
            "SMTP_FROM", "cobranca@controldesk.example.com"
        )

        # ── CORS ────────────────────────────────────────────────
        self.CORS_ORIGINS: List[str] = [
            o.strip()
            for o in os.getenv(
                "CORS_ORIGINS",
                "http://localhost:5173,http://127.0.0.1:5173,http://localhost:3000",
            ).split(",")
            if o.strip()
        ]

        # ── LGPD ────────────────────────────────────────────────
        self.DATA_CONTROLLER_NAME: str = os.getenv(
            "DATA_CONTROLLER_NAME", "ControlDesk Cobranças LTDA"
        )
        self.DPO_EMAIL: str = os.getenv("DPO_EMAIL", "dpo@controldesk.example.com")
        # Retenção padrão de dados pessoais após quitação (dias).
        self.LGPD_RETENTION_DAYS: int = int(os.getenv("LGPD_RETENTION_DAYS", "1825"))

        # ── Seed / bootstrap ────────────────────────────────────
        self.FIRST_ADMIN_EMAIL: str = os.getenv(
            "FIRST_ADMIN_EMAIL", "admin@controldesk.example.com"
        )
        self.FIRST_ADMIN_PASSWORD: str = os.getenv(
            "FIRST_ADMIN_PASSWORD", "Admin@123456"
        )

    @property
    def is_sqlite(self) -> bool:
        return self.DATABASE_URL.startswith("sqlite")

    @property
    def is_production(self) -> bool:
        return self.APP_ENV.lower() in ("production", "prod")

    def validate_for_production(self) -> None:
        """Falha rápido se segredos padrão de dev forem usados em produção."""
        if not self.is_production:
            return
        insecure = {
            "JWT_SECRET_KEY": ("TROQUE" in self.JWT_SECRET_KEY
                               or self.JWT_SECRET_KEY.startswith("dev-")),
            "DATA_ENCRYPTION_KEY": "TROQUE" in self.DATA_ENCRYPTION_KEY,
            "DATA_INDEX_KEY": "TROQUE" in self.DATA_INDEX_KEY,
            "FIRST_ADMIN_PASSWORD": self.FIRST_ADMIN_PASSWORD == "Admin@123456",
        }
        offenders = [name for name, bad in insecure.items() if bad]
        if offenders:
            raise RuntimeError(
                "Segredos inseguros detectados em produção: "
                + ", ".join(offenders)
                + ". Defina valores fortes via variáveis de ambiente."
            )


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
