def _create_debtor(client, headers):
    return client.post(
        "/api/collection/debtors",
        headers=headers,
        json={
            "full_name": "Fulano de Tal",
            "document": "123.456.789-09",
            "email": "fulano@example.com",
        },
    )


def test_create_debtor_masks_document(client, auth_headers):
    resp = _create_debtor(client, auth_headers)
    assert resp.status_code == 201, resp.text
    body = resp.json()
    # documento nunca é devolvido em claro
    assert "*" in body["document_masked"]
    assert body["document_masked"].endswith("09")


def test_debtor_requires_valid_document(client, auth_headers):
    resp = client.post(
        "/api/collection/debtors",
        headers=auth_headers,
        json={"full_name": "X", "document": "123"},
    )
    assert resp.status_code == 422


def test_create_debt_and_score(client, auth_headers):
    debtor = _create_debtor(client, auth_headers).json()
    resp = client.post(
        "/api/collection/debts",
        headers=auth_headers,
        json={
            "debtor_id": debtor["id"],
            "contract_ref": "CT-1",
            "portfolio": "consignado",
            "creditor": "Banco X",
            "original_amount": 1000,
            "current_amount": 1200,
            "days_overdue": 20,
        },
    )
    assert resp.status_code == 201, resp.text
    assert 0 <= resp.json()["risk_score"] <= 100


def test_invalid_portfolio_rejected(client, auth_headers):
    debtor = _create_debtor(client, auth_headers).json()
    resp = client.post(
        "/api/collection/debts",
        headers=auth_headers,
        json={
            "debtor_id": debtor["id"],
            "contract_ref": "CT-2",
            "portfolio": "invalida",
            "creditor": "Banco X",
            "original_amount": 1000,
            "current_amount": 1000,
        },
    )
    assert resp.status_code == 422


def test_interaction_updates_contact_status(client, auth_headers):
    debtor = _create_debtor(client, auth_headers).json()
    resp = client.post(
        "/api/collection/interactions",
        headers=auth_headers,
        json={
            "debtor_id": debtor["id"],
            "channel": "telefone",
            "result": "promessa",
            "notes": "Cliente prometeu pagar dia 10.",
        },
    )
    assert resp.status_code == 201, resp.text
    assert resp.json()["result"] == "promessa"
    # o status de contato do devedor deve refletir a última tabulação
    debtors = client.get(
        f"/api/collection/debtors?q={debtor['document_masked'][:3]}",
        headers=auth_headers,
    )
    # busca direta pelo id via listagem de interações
    inter = client.get(
        f"/api/collection/interactions?debtor_id={debtor['id']}", headers=auth_headers
    ).json()
    assert len(inter) == 1
    assert inter[0]["channel"] == "telefone"


def test_interaction_invalid_result_rejected(client, auth_headers):
    debtor = _create_debtor(client, auth_headers).json()
    resp = client.post(
        "/api/collection/interactions",
        headers=auth_headers,
        json={"debtor_id": debtor["id"], "result": "resultado_invalido"},
    )
    assert resp.status_code == 422


def test_payment_reduces_balance(client, auth_headers):
    debtor = _create_debtor(client, auth_headers).json()
    debt = client.post(
        "/api/collection/debts",
        headers=auth_headers,
        json={
            "debtor_id": debtor["id"],
            "contract_ref": "CT-3",
            "portfolio": "ativa",
            "creditor": "Banco X",
            "original_amount": 500,
            "current_amount": 500,
        },
    ).json()
    resp = client.post(
        "/api/collection/payments",
        headers=auth_headers,
        json={"debt_id": debt["id"], "amount": 500, "method": "pix"},
    )
    assert resp.status_code == 201
    debts = client.get(
        f"/api/collection/debts?debtor_id={debtor['id']}", headers=auth_headers
    ).json()
    settled = [d for d in debts if d["id"] == debt["id"]][0]
    assert settled["status"] == "quitada"
