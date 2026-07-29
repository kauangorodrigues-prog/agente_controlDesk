"""Garante que as migrations Alembic aplicam e batem com os modelos ORM.

Roda o Alembic num banco SQLite temporário e isolado (via subprocesso, para
não colidir com o banco de testes já carregado pelo conftest). `alembic check`
falha se houver divergência entre os modelos e a migration — prevenindo drift.
"""
from __future__ import annotations

import os
import pathlib
import subprocess
import sys
import tempfile

BACKEND_DIR = pathlib.Path(__file__).resolve().parents[1]


def _run_alembic(args: list[str], db_url: str) -> subprocess.CompletedProcess:
    env = {**os.environ, "DATABASE_URL": db_url, "APP_ENV": "development"}
    return subprocess.run(
        [sys.executable, "-m", "alembic", *args],
        cwd=BACKEND_DIR,
        env=env,
        capture_output=True,
        text=True,
    )


def test_migrations_upgrade_and_match_models():
    fd, db_path = tempfile.mkstemp(suffix=".db")
    os.close(fd)
    db_url = f"sqlite:///{db_path}"
    try:
        up = _run_alembic(["upgrade", "head"], db_url)
        assert up.returncode == 0, f"upgrade falhou:\n{up.stderr}"

        # `alembic check` retorna != 0 se os modelos divergem da migration.
        check = _run_alembic(["check"], db_url)
        assert check.returncode == 0, (
            "Schema fora de sincronia com os modelos "
            f"(gere nova migration):\n{check.stdout}\n{check.stderr}"
        )
    finally:
        os.unlink(db_path)
