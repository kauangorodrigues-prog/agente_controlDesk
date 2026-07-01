from __future__ import annotations

import time

import requests

from .alerts import ALERTAS
from .circuit_breaker import CircuitBreaker
from .config import CFG
from .logging_setup import get_logger

log = get_logger("clients")


class OlosClient:
    """Cliente do discador Olos: agentes, chamadas, snapshot de campanhas, mailing e pacing."""

    BASE = CFG.OLOS_BASE_URL
    HEADERS = {"Authorization": f"Bearer {CFG.OLOS_TOKEN}", "Content-Type": "application/json"}
    TIMEOUT = 15

    _cb = CircuitBreaker(CFG.CB_MAX_FALHAS, CFG.CB_PAUSA_MIN, "Olos")
    _cache: dict[str, dict] = {}

    @classmethod
    def circuito_aberto(cls) -> bool:
        return cls._cb.aberto

    @classmethod
    def _get(cls, endpoint: str, params: dict | None = None) -> dict:
        if cls._cb.aberto:
            log.warning(f"[Olos] Circuito aberto — request a {endpoint} ignorado.")
            return {}
        for tentativa in range(1, 4):
            try:
                r = requests.get(
                    f"{cls.BASE}{endpoint}", headers=cls.HEADERS, params=params, timeout=cls.TIMEOUT
                )
                r.raise_for_status()
                cls._cb.registrar_sucesso()
                return r.json()
            except (requests.Timeout, requests.ConnectionError) as e:
                log.warning(f"[Olos] Tentativa {tentativa}/3 falhou em {endpoint}: {e}")
                time.sleep(2 ** tentativa)
            except Exception as e:
                log.error(f"[Olos] Erro em {endpoint}: {e}")
                cls._cb.registrar_falha(ALERTAS)
                return {}
        cls._cb.registrar_falha(ALERTAS)
        return {}

    @classmethod
    def _put(cls, endpoint: str, payload: dict) -> dict:
        if cls._cb.aberto:
            log.warning(f"[Olos] Circuito aberto — PUT a {endpoint} ignorado.")
            return {}
        for tentativa in range(1, 4):
            try:
                r = requests.put(
                    f"{cls.BASE}{endpoint}", headers=cls.HEADERS, json=payload, timeout=cls.TIMEOUT
                )
                r.raise_for_status()
                cls._cb.registrar_sucesso()
                return r.json()
            except (requests.Timeout, requests.ConnectionError) as e:
                log.warning(f"[Olos] PUT tentativa {tentativa}/3 falhou: {e}")
                time.sleep(2 ** tentativa)
            except Exception as e:
                log.error(f"[Olos] Erro PUT {endpoint}: {e}")
                cls._cb.registrar_falha(ALERTAS)
                return {}
        cls._cb.registrar_falha(ALERTAS)
        return {}

    @classmethod
    def get_agents(cls) -> list:
        d = cls._get("/agents")
        return d.get("agents", d if isinstance(d, list) else [])

    @classmethod
    def get_calls(cls, data_inicio: str | None = None) -> list:
        params = {"from": data_inicio} if data_inicio else {}
        d = cls._get("/calls/history", params=params)
        return d.get("calls", d if isinstance(d, list) else [])

    @classmethod
    def get_campaign_snapshot(cls) -> list:
        """Cache com TTL configurável — evita sobrecarregar a API do Olos."""
        entry = cls._cache.get("campaign_snapshot")
        if entry and (time.time() - entry["ts"]) < CFG.CACHE_TTL_SEG:
            return entry["data"]
        d = cls._get("/campaigns/snapshot")
        data = d.get("data", d if isinstance(d, list) else [])
        if data:
            cls._cache["campaign_snapshot"] = {"data": data, "ts": time.time()}
        return data

    @classmethod
    def get_mailing_status(cls) -> list:
        d = cls._get("/mailing/status")
        return d.get("mailings", d if isinstance(d, list) else [])

    @classmethod
    def update_pacing(cls, campaign_id: str, pacing: float) -> dict:
        result = cls._put(f"/campaigns/{campaign_id}/pacing", {"pacing": round(pacing, 1)})
        log.info(f"[Olos] Pacing: campanha={campaign_id} pacing={pacing}")
        return result

    @classmethod
    def pause_campaign(cls, campaign_id: str, motivo: str = "") -> dict:
        result = cls._put(f"/campaigns/{campaign_id}/pause", {"reason": motivo})
        log.info(f"[Olos] Campanha pausada: {campaign_id} — {motivo}")
        return result

    @classmethod
    def resume_campaign(cls, campaign_id: str) -> dict:
        result = cls._put(f"/campaigns/{campaign_id}/resume", {})
        log.info(f"[Olos] Campanha retomada: {campaign_id}")
        return result


class EasyClient:
    """Cliente do EasyCollector: clientes/carteira, promessas de pagamento."""

    BASE = CFG.EASY_BASE_URL
    HEADERS = {"Authorization": f"Bearer {CFG.EASY_TOKEN}", "Content-Type": "application/json"}
    TIMEOUT = 15

    _cb = CircuitBreaker(CFG.CB_MAX_FALHAS, CFG.CB_PAUSA_MIN, "Easy")

    @classmethod
    def circuito_aberto(cls) -> bool:
        return cls._cb.aberto

    @classmethod
    def _get(cls, endpoint: str, params: dict | None = None) -> dict:
        if cls._cb.aberto:
            log.warning(f"[Easy] Circuito aberto — request a {endpoint} ignorado.")
            return {}
        for tentativa in range(1, 4):
            try:
                r = requests.get(
                    f"{cls.BASE}{endpoint}", headers=cls.HEADERS, params=params, timeout=cls.TIMEOUT
                )
                r.raise_for_status()
                cls._cb.registrar_sucesso()
                return r.json()
            except (requests.Timeout, requests.ConnectionError) as e:
                log.warning(f"[Easy] Tentativa {tentativa}/3 falhou: {e}")
                time.sleep(2 ** tentativa)
            except Exception as e:
                log.error(f"[Easy] Erro {endpoint}: {e}")
                cls._cb.registrar_falha(ALERTAS)
                return {}
        cls._cb.registrar_falha(ALERTAS)
        return {}

    @classmethod
    def get_customers(cls, campanha_id: str | None = None) -> list:
        params = {"campaign_id": campanha_id} if campanha_id else {}
        d = cls._get("/customers", params=params)
        return d.get("customers", d if isinstance(d, list) else [])

    @classmethod
    def get_promises(cls, data: str | None = None) -> list:
        params = {"date": data} if data else {}
        d = cls._get("/promises", params=params)
        return d.get("promises", d if isinstance(d, list) else [])

    @classmethod
    def get_portfolios(cls) -> list:
        d = cls._get("/portfolios/active")
        return d.get("portfolios", d if isinstance(d, list) else [])
