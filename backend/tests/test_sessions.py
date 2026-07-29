"""Testes de refresh tokens e logout com revogação server-side."""


def _login(client):
    return client.post(
        "/api/auth/login",
        json={"email": "admin@test.com", "password": "Admin@123456"},
    ).json()


def test_login_returns_refresh_token(client):
    body = _login(client)
    assert body.get("refresh_token")
    assert body.get("access_token")


def test_refresh_rotates_and_invalidates_old(client):
    body = _login(client)
    old_refresh = body["refresh_token"]

    r = client.post("/api/auth/refresh", json={"refresh_token": old_refresh})
    assert r.status_code == 200
    new_refresh = r.json()["refresh_token"]
    assert new_refresh and new_refresh != old_refresh

    # o refresh antigo foi revogado na rotação
    reuse = client.post("/api/auth/refresh", json={"refresh_token": old_refresh})
    assert reuse.status_code == 401


def test_logout_revokes_refresh_token(client):
    body = _login(client)
    refresh = body["refresh_token"]

    out = client.post("/api/auth/logout", json={"refresh_token": refresh})
    assert out.status_code == 204

    # após logout, o refresh não é mais aceito
    after = client.post("/api/auth/refresh", json={"refresh_token": refresh})
    assert after.status_code == 401


def test_logout_all_revokes_every_session(client):
    a = _login(client)
    b = _login(client)
    headers = {"Authorization": f"Bearer {b['access_token']}"}

    out = client.post("/api/auth/logout-all", headers=headers)
    assert out.status_code == 204

    for session in (a, b):
        r = client.post(
            "/api/auth/refresh", json={"refresh_token": session["refresh_token"]}
        )
        assert r.status_code == 401
