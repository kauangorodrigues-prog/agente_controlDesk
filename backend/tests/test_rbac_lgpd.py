def _make_admin_user(client, auth_headers, email):
    return client.post(
        "/api/users",
        headers=auth_headers,
        json={
            "full_name": "Operador Restrito",
            "email": email,
            "password": "Senha@123",
            "role": "administracao",
            "sectors": ["control_desk"],
        },
    )


def _token_for(client, email, password):
    resp = client.post("/api/auth/login", json={"email": email, "password": password})
    return {"Authorization": f"Bearer {resp.json()['access_token']}"}


def test_admin_cannot_create_users(client, auth_headers):
    _make_admin_user(client, auth_headers, "restrito@test.com")
    headers = _token_for(client, "restrito@test.com", "Senha@123")
    resp = client.post(
        "/api/users",
        headers=headers,
        json={"full_name": "Y", "email": "y@test.com", "password": "Senha@123"},
    )
    assert resp.status_code == 403


def test_sector_guard_blocks_unauthorized(client, auth_headers):
    _make_admin_user(client, auth_headers, "setor@test.com")
    headers = _token_for(client, "setor@test.com", "Senha@123")
    # tem control_desk, mas NÃO tem planejamento
    assert client.get("/api/control-desk/campaigns", headers=headers).status_code == 200
    assert client.get("/api/planejamento/forecasts", headers=headers).status_code == 403


def test_privacy_notice_is_public(client):
    resp = client.get("/api/lgpd/privacy-notice")
    assert resp.status_code == 200
    assert "encarregado_dpo" in resp.json()


def test_dsr_can_be_opened_publicly(client):
    resp = client.post(
        "/api/lgpd/requests",
        json={"requester_document": "123.456.789-09", "request_type": "acesso"},
    )
    assert resp.status_code == 201
    assert resp.json()["status"] == "recebida"


def test_anonymize_flow(client, auth_headers):
    debtor = client.post(
        "/api/collection/debtors",
        headers=auth_headers,
        json={"full_name": "Para Anonimizar", "document": "98765432100"},
    ).json()
    resp = client.post(f"/api/lgpd/anonymize/{debtor['id']}", headers=auth_headers)
    assert resp.status_code == 200
    assert resp.json()["anonymized"] is True
    # segunda tentativa deve conflitar
    again = client.post(f"/api/lgpd/anonymize/{debtor['id']}", headers=auth_headers)
    assert again.status_code == 409
