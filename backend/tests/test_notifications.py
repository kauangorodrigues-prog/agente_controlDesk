"""Testes da régua de comunicação (notificações)."""


def _debtor(client, headers, doc="390.533.447-05"):
    return client.post(
        "/api/collection/debtors",
        headers=headers,
        json={"full_name": "Notificado Silva", "document": doc,
              "email": "notificado@example.com"},
    ).json()


def test_notification_blocked_without_consent(client, auth_headers):
    """Sem base legal de comunicação, o envio é bloqueado (guardrail LGPD)."""
    debtor = _debtor(client, auth_headers)
    resp = client.post(
        "/api/notifications",
        headers=auth_headers,
        json={"debtor_id": debtor["id"], "template": "lembrete"},
    )
    assert resp.status_code == 201, resp.text
    assert resp.json()["status"] == "bloqueado_lgpd"


def test_notification_sent_with_consent(client, auth_headers):
    debtor = _debtor(client, auth_headers, doc="111.444.777-35")
    # registra consentimento de comunicação
    client.post(
        "/api/lgpd/consents",
        headers=auth_headers,
        json={"debtor_id": debtor["id"], "purpose": "comunicacao",
              "legal_basis": "consentimento", "granted": True},
    )
    resp = client.post(
        "/api/notifications",
        headers=auth_headers,
        json={"debtor_id": debtor["id"], "template": "proposta"},
    )
    assert resp.status_code == 201
    # sem SMTP configurado, o envio é simulado (dry-run)
    assert resp.json()["status"] == "simulado"
    # e fica registrado no histórico
    hist = client.get(
        f"/api/notifications?debtor_id={debtor['id']}", headers=auth_headers
    ).json()
    assert len(hist) == 1
    assert hist[0]["template"] == "proposta"


def test_invalid_template_rejected(client, auth_headers):
    debtor = _debtor(client, auth_headers, doc="529.982.247-25")
    resp = client.post(
        "/api/notifications",
        headers=auth_headers,
        json={"debtor_id": debtor["id"], "template": "inexistente"},
    )
    assert resp.status_code == 400
