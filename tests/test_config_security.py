"""Testes da validação de segurança de configuração e da construção do app."""
import importlib

import pytest

mod = importlib.import_module("agente_ia_control_desk")


# ── Detecção de defaults inseguros ──────────────────────────
def test_problemas_seguranca_detecta_jwt_default(monkeypatch):
    monkeypatch.setattr(mod.CFG, "JWT_SECRET_KEY", "TROQUE_EM_PRODUCAO")
    problemas = mod.CFG.problemas_seguranca()
    assert any("JWT_SECRET_KEY" in p for p in problemas)


def test_problemas_seguranca_limpo(monkeypatch):
    monkeypatch.setattr(mod.CFG, "JWT_SECRET_KEY", "um-segredo-bem-forte-123")
    monkeypatch.setattr(mod.CFG, "POSTGRES_PASSWORD", "senha-real-forte")
    monkeypatch.setattr(mod.CFG, "CORS_ORIGINS", "https://app.exemplo.com")
    assert mod.CFG.problemas_seguranca() == []


# ── Comportamento por ambiente ──────────────────────────────
def test_validar_seguranca_aborta_em_producao(monkeypatch):
    monkeypatch.setattr(mod.CFG, "AMBIENTE", "production")
    monkeypatch.setattr(mod.CFG, "JWT_SECRET_KEY", "TROQUE_EM_PRODUCAO")
    with pytest.raises(RuntimeError):
        mod.CFG.validar_seguranca()


def test_validar_seguranca_apenas_avisa_em_dev(monkeypatch):
    monkeypatch.setattr(mod.CFG, "AMBIENTE", "development")
    monkeypatch.setattr(mod.CFG, "JWT_SECRET_KEY", "TROQUE_EM_PRODUCAO")
    # Não deve levantar em desenvolvimento — apenas registra aviso.
    assert mod.CFG.validar_seguranca() is None


# ── CORS ────────────────────────────────────────────────────
def test_cors_origins_list_parsing(monkeypatch):
    monkeypatch.setattr(mod.CFG, "CORS_ORIGINS", "https://a.com, https://b.com")
    assert mod.CFG.CORS_ORIGINS_LIST == ["https://a.com", "https://b.com"]


# ── App FastAPI (só roda se o fastapi estiver instalado) ────
def test_app_construido_quando_fastapi_disponivel():
    pytest.importorskip("fastapi")
    assert mod.FASTAPI_DISPONIVEL is True
    assert mod.app is not None
