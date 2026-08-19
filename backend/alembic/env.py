"""Ambiente de execução das migrations Alembic.

Usa a mesma configuração e metadata da aplicação, de modo que
`alembic revision --autogenerate` detecte mudanças nos modelos ORM.
"""
from __future__ import annotations

from logging.config import fileConfig

from alembic import context
from sqlalchemy import engine_from_config, pool

from app.core.config import settings
from app.core.database import Base
from app import models  # noqa: F401  (registra todos os modelos na metadata)

config = context.config
# Injeta a URL do banco a partir das configurações da aplicação.
config.set_main_option("sqlalchemy.url", settings.DATABASE_URL)

if config.config_file_name is not None:
    fileConfig(config.config_file_name)

target_metadata = Base.metadata


def render_item(type_, obj, autogen_context):
    """Garante o import do tipo customizado EncryptedStr nas migrations."""
    from app.core.crypto import EncryptedStr

    if type_ == "type" and isinstance(obj, EncryptedStr):
        autogen_context.imports.add("import app.core.crypto")
        return f"app.core.crypto.EncryptedStr(length={obj.impl.length})"
    return False


def run_migrations_offline() -> None:
    context.configure(
        url=settings.DATABASE_URL,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
        render_item=render_item,
        render_as_batch=True,
    )
    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    connectable = engine_from_config(
        config.get_section(config.config_ini_section, {}),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )
    with connectable.connect() as connection:
        context.configure(
            connection=connection,
            target_metadata=target_metadata,
            render_item=render_item,
            render_as_batch=True,  # necessário para ALTER em SQLite
        )
        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
