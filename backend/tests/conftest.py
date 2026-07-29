"""Fixtures de teste: banco isolado em arquivo temporário + client autenticado."""
from __future__ import annotations

import os
import tempfile

import pytest

# Configura um banco SQLite temporário ANTES de importar a aplicação.
_db_fd, _db_path = tempfile.mkstemp(suffix=".db")
os.environ["DATABASE_URL"] = f"sqlite:///{_db_path}"
os.environ["JWT_SECRET_KEY"] = "test-secret"
os.environ["APP_ENV"] = "test"

from fastapi.testclient import TestClient  # noqa: E402

from app.core.database import SessionLocal, init_db  # noqa: E402
from app.core.rbac import Role, Sector  # noqa: E402
from app.core.security import hash_password  # noqa: E402
from app.main import app  # noqa: E402
from app.models.access import SectorAccess  # noqa: E402
from app.models.user import User  # noqa: E402


@pytest.fixture(scope="session", autouse=True)
def _setup_db():
    init_db()
    db = SessionLocal()
    try:
        admin = User(
            full_name="Admin Teste",
            email="admin@test.com",
            hashed_password=hash_password("Admin@123456"),
            role=Role.DIRETORIA.value,
        )
        for s in Sector:
            admin.sector_accesses.append(SectorAccess(sector=s.value))
        db.add(admin)
        db.commit()
    finally:
        db.close()
    yield
    os.close(_db_fd)
    os.unlink(_db_path)


@pytest.fixture
def client():
    return TestClient(app)


@pytest.fixture
def auth_headers(client):
    resp = client.post(
        "/api/auth/login",
        json={"email": "admin@test.com", "password": "Admin@123456"},
    )
    assert resp.status_code == 200, resp.text
    token = resp.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}
