"""Criptografia de dados pessoais em repouso (LGPD art. 46).

Estratégia:
  * PII sensível (documento) é cifrado com Fernet (AES-128 CBC + HMAC).
  * Para permitir busca/igualdade sem descriptografar, mantém-se um
    "índice cego" (blind index) = HMAC-SHA256 do valor normalizado.

A cifragem é transparente via o tipo SQLAlchemy `EncryptedStr`: o valor
é cifrado ao gravar e decifrado ao ler, sem mudar o código de negócio.
"""
from __future__ import annotations

import base64
import hashlib
import hmac

from cryptography.fernet import Fernet, InvalidToken
from sqlalchemy import String
from sqlalchemy.types import TypeDecorator

from app.core.config import settings


def _fernet() -> Fernet:
    # Deriva uma chave Fernet válida (32 bytes url-safe base64) da chave configurada.
    digest = hashlib.sha256(settings.DATA_ENCRYPTION_KEY.encode()).digest()
    return Fernet(base64.urlsafe_b64encode(digest))


def encrypt(plaintext: str) -> str:
    return _fernet().encrypt(plaintext.encode()).decode()


def decrypt(ciphertext: str) -> str:
    return _fernet().decrypt(ciphertext.encode()).decode()


def blind_index(value: str) -> str:
    """HMAC-SHA256 determinístico para busca por igualdade de valor cifrado."""
    return hmac.new(
        settings.DATA_INDEX_KEY.encode(), value.encode(), hashlib.sha256
    ).hexdigest()


class EncryptedStr(TypeDecorator):
    """Coluna de texto cifrada em repouso, transparente para a aplicação."""

    impl = String
    cache_ok = True

    def process_bind_param(self, value: str | None, dialect) -> str | None:
        if value is None:
            return None
        return encrypt(value)

    def process_result_value(self, value: str | None, dialect) -> str | None:
        if value is None:
            return None
        try:
            return decrypt(value)
        except (InvalidToken, ValueError):
            # Tolera dados legados gravados em texto puro (migração suave).
            return value
