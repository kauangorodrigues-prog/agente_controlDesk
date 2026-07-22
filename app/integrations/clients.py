"""Clientes de integração com discador e cobrador/CRM.

Camada `integrations`: depende de `app.config` (CFG), do logger e de `requests`.
Não conhece serviços/API.
"""
from __future__ import annotations

import logging
import time

import requests

from app.config import CFG

log = logging.getLogger("ControlDesk")


class DialerClient:
    BASE    = CFG.DIALER_BASE_URL
    HEADERS = {
        "Authorization": f"Bearer {CFG.DIALER_TOKEN}",
        "Content-Type": "application/json",
    }
    TIMEOUT = 15

    @classmethod
    def _get(cls, endpoint: str, params: dict = None) -> dict:
        for tentativa in range(1, 4):
            try:
                r = requests.get(
                    f"{cls.BASE}{endpoint}",
                    headers=cls.HEADERS,
                    params=params,
                    timeout=cls.TIMEOUT,
                )
                r.raise_for_status()
                return r.json()
            except (requests.Timeout, requests.ConnectionError) as e:
                log.warning(f"[Dialer] Tentativa {tentativa}/3 falhou em {endpoint}: {e}")
                time.sleep(2 ** tentativa)
            except Exception as e:
                log.error(f"[Dialer] Erro em {endpoint}: {e}")
                return {}
        return {}

    @classmethod
    def _put(cls, endpoint: str, payload: dict) -> dict:
        for tentativa in range(1, 4):
            try:
                r = requests.put(
                    f"{cls.BASE}{endpoint}",
                    headers=cls.HEADERS,
                    json=payload,
                    timeout=cls.TIMEOUT,
                )
                r.raise_for_status()
                return r.json()
            except (requests.Timeout, requests.ConnectionError) as e:
                log.warning(f"[Dialer] PUT tentativa {tentativa}/3 falhou: {e}")
                time.sleep(2 ** tentativa)
            except Exception as e:
                log.error(f"[Dialer] Erro PUT {endpoint}: {e}")
                return {}
        return {}

    @classmethod
    def get_agents(cls) -> list:
        d = cls._get("/agents")
        return d.get("agents", d if isinstance(d, list) else [])

    @classmethod
    def get_calls(cls, data_inicio: str = None) -> list:
        params = {"from": data_inicio} if data_inicio else {}
        d = cls._get("/calls/history", params=params)
        return d.get("calls", d if isinstance(d, list) else [])

    @classmethod
    def get_campaign_snapshot(cls) -> list:
        d = cls._get("/campaigns/snapshot")
        return d.get("data", d if isinstance(d, list) else [])

    @classmethod
    def get_mailing_status(cls) -> list:
        d = cls._get("/mailing/status")
        return d.get("mailings", d if isinstance(d, list) else [])

    @classmethod
    def update_pacing(cls, campaign_id: str, pacing: float) -> dict:
        result = cls._put(f"/campaigns/{campaign_id}/pacing", {"pacing": round(pacing, 1)})
        log.info(f"[Dialer] Pacing: campanha={campaign_id} pacing={pacing}")
        return result

    @classmethod
    def pause_campaign(cls, campaign_id: str, motivo: str = "") -> dict:
        result = cls._put(f"/campaigns/{campaign_id}/pause", {"reason": motivo})
        log.info(f"[Dialer] Campanha pausada: {campaign_id} — {motivo}")
        return result

    @classmethod
    def resume_campaign(cls, campaign_id: str) -> dict:
        result = cls._put(f"/campaigns/{campaign_id}/resume", {})
        log.info(f"[Dialer] Campanha retomada: {campaign_id}")
        return result


class CollectorClient:
    BASE    = CFG.COLLECTOR_BASE_URL
    HEADERS = {
        "Authorization": f"Bearer {CFG.COLLECTOR_TOKEN}",
        "Content-Type": "application/json",
    }
    TIMEOUT = 15

    @classmethod
    def _get(cls, endpoint: str, params: dict = None) -> dict:
        for tentativa in range(1, 4):
            try:
                r = requests.get(
                    f"{cls.BASE}{endpoint}",
                    headers=cls.HEADERS,
                    params=params,
                    timeout=cls.TIMEOUT,
                )
                r.raise_for_status()
                return r.json()
            except (requests.Timeout, requests.ConnectionError) as e:
                log.warning(f"[Collector] Tentativa {tentativa}/3 falhou: {e}")
                time.sleep(2 ** tentativa)
            except Exception as e:
                log.error(f"[Collector] Erro {endpoint}: {e}")
                return {}
        return {}

    @classmethod
    def get_customers(cls, campanha_id: str = None) -> list:
        params = {"campaign_id": campanha_id} if campanha_id else {}
        d = cls._get("/customers", params=params)
        return d.get("customers", d if isinstance(d, list) else [])

    @classmethod
    def get_promises(cls, data: str = None) -> list:
        params = {"date": data} if data else {}
        d = cls._get("/promises", params=params)
        return d.get("promises", d if isinstance(d, list) else [])

    @classmethod
    def get_portfolios(cls) -> list:
        d = cls._get("/portfolios/active")
        return d.get("portfolios", d if isinstance(d, list) else [])
