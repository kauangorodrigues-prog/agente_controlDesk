"""Alertas via webhook (com throttle e trilha no banco).

Camada `alerts`: depende de `app.config` (CFG), do logger, de `requests` e de
`app.core.database` (persistência da trilha em alert_log).
"""
from __future__ import annotations

import logging
from datetime import datetime

import requests

from app.config import CFG
from app.core.database import executar_comando

log = logging.getLogger("ControlDesk")

_throttle_cache: dict = {}
ICONES_ALERTA = {"INFO": "ℹ️", "ATENCAO": "⚠️", "CRITICO": "🔴"}


def _registrar_alerta_banco(chave: str, nivel: str, mensagem: str, enviado: bool):
    try:
        executar_comando(
            "INSERT INTO alert_log (chave, nivel, mensagem, canal, enviado, ts) "
            "VALUES (:chave, :nivel, :mensagem, 'webhook', :enviado, NOW())",
            {"chave": chave, "nivel": nivel, "mensagem": mensagem, "enviado": enviado},
        )
    except Exception as e:
        log.debug(f"Falha ao registrar alerta no banco: {e}")


def pode_enviar_alerta(chave: str, throttle_seg: int = None) -> bool:
    throttle = throttle_seg or CFG.THROTTLE_ALERTAS_SEG
    agora = datetime.utcnow()
    ultimo = _throttle_cache.get(chave)
    if ultimo and (agora - ultimo).total_seconds() < throttle:
        return False
    _throttle_cache[chave] = agora
    return True


def send_webhook_alert(
    mensagem: str,
    nivel: str = "INFO",
    chave: str = "geral",
    throttle_seg: int = None,
    forcar: bool = False,
) -> bool:
    if not CFG.WEBHOOK_ALERTA:
        log.warning("WEBHOOK_ALERTA não configurado.")
        return False

    if not forcar and not pode_enviar_alerta(chave, throttle_seg):
        return False

    icone = ICONES_ALERTA.get(nivel.upper(), "📢")
    payload = {"text": f"{icone} **[{nivel.upper()}]** {mensagem}"}

    for tentativa in range(1, 4):
        try:
            r = requests.post(CFG.WEBHOOK_ALERTA, json=payload, timeout=10)
            r.raise_for_status()
            log.info(f"[Webhook] Enviado: chave={chave} nivel={nivel}")
            _registrar_alerta_banco(chave, nivel, mensagem, True)
            return True
        except requests.Timeout:
            log.warning(f"[Webhook] Timeout na tentativa {tentativa}/3")
        except Exception as e:
            log.error(f"[Webhook] Erro tentativa {tentativa}/3: {e}")
            break

    _registrar_alerta_banco(chave, nivel, mensagem, False)
    return False
