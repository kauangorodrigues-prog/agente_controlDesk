"""Testes de observabilidade: request-id e métricas."""


def test_request_id_header_present(client):
    resp = client.get("/health")
    assert resp.status_code == 200
    assert resp.headers.get("X-Request-ID")
    assert resp.headers.get("X-Response-Time-ms")


def test_request_id_is_echoed_when_provided(client):
    resp = client.get("/health", headers={"X-Request-ID": "abc123"})
    assert resp.headers.get("X-Request-ID") == "abc123"


def test_metrics_endpoint(client):
    # gera tráfego para popular as métricas
    client.get("/health")
    resp = client.get("/metrics")
    assert resp.status_code == 200
    body = resp.json()
    assert "uptime_seconds" in body
    assert "avg_latency_ms" in body
    assert body["total_requests"] >= 1
