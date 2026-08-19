"""Testes de segurança: criptografia de PII, índice cego e rate-limiting."""
from app.core import crypto
from app.core.config import Settings


def test_document_encrypted_at_rest_but_readable_via_api(client, auth_headers):
    resp = client.post(
        "/api/collection/debtors",
        headers=auth_headers,
        json={"full_name": "Cripto Teste", "document": "111.444.777-35"},
    )
    assert resp.status_code == 201, resp.text
    debtor_id = resp.json()["id"]

    # No banco, o valor está cifrado (não contém os dígitos em claro).
    from app.core.database import SessionLocal
    from app.models.debtor import Debtor
    from sqlalchemy import text

    db = SessionLocal()
    try:
        raw = db.execute(
            text("SELECT document FROM debtors WHERE id = :i"), {"i": debtor_id}
        ).scalar()
        assert "11144477735" not in (raw or "")
        # Ao ler pelo ORM, o valor é decifrado de forma transparente.
        debtor = db.get(Debtor, debtor_id)
        assert debtor.document == "11144477735"
    finally:
        db.close()


def test_blind_index_enables_search(client, auth_headers):
    client.post(
        "/api/collection/debtors",
        headers=auth_headers,
        json={"full_name": "Busca Documento", "document": "52998224725"},
    )
    resp = client.get(
        "/api/collection/debtors?q=529.982.247-25", headers=auth_headers
    )
    assert resp.status_code == 200
    names = [d["full_name"] for d in resp.json()]
    assert "Busca Documento" in names


def test_login_lockout_after_max_attempts(client):
    email = "brute@test.com"
    # 5 tentativas falhas (limite padrão) -> a 6ª deve ser bloqueada (429).
    for _ in range(5):
        r = client.post("/api/auth/login", json={"email": email, "password": "x"})
        assert r.status_code == 401
    blocked = client.post("/api/auth/login", json={"email": email, "password": "x"})
    assert blocked.status_code == 429
    assert "Retry-After" in blocked.headers


def test_production_config_rejects_default_secrets():
    import os

    prev = os.environ.get("APP_ENV")
    os.environ["APP_ENV"] = "production"
    try:
        s = Settings()  # usa segredos padrão de dev
        try:
            s.validate_for_production()
            assert False, "deveria ter falhado com segredos padrão"
        except RuntimeError as e:
            # Deve apontar ao menos uma chave insegura padrão de desenvolvimento.
            assert "DATA_ENCRYPTION_KEY" in str(e)
    finally:
        if prev is None:
            os.environ.pop("APP_ENV", None)
        else:
            os.environ["APP_ENV"] = prev
