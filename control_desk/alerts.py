from __future__ import annotations

import smtplib
import threading
import time
from collections import deque
from datetime import datetime
from email import encoders
from email.mime.base import MIMEBase
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from typing import Optional

import requests

from .config import CFG
from .db import executar_comando
from .logging_setup import get_logger

ICONES_ALERTA = {"INFO": "ℹ️", "ATENCAO": "⚠️", "CRITICO": "🔴"}


class GestorAlertas:
    """Centraliza Teams/Email com throttle por chave e dead letter queue (DLQ)."""

    def __init__(self) -> None:
        self._log = get_logger("alertas")
        self._throttle: dict[str, datetime] = {}
        self._dlq: deque = deque(maxlen=200)
        self._dlq_lock = threading.Lock()
        threading.Thread(target=self._dlq_loop, daemon=True, name="alertas-dlq").start()

    # ── throttle ──────────────────────────────────────────────────────────

    def _pode_enviar(self, chave: str, throttle_seg: Optional[int]) -> bool:
        throttle = throttle_seg if throttle_seg is not None else CFG.THROTTLE_ALERTAS_SEG
        agora = datetime.utcnow()
        ultimo = self._throttle.get(chave)
        if ultimo and (agora - ultimo).total_seconds() < throttle:
            return False
        self._throttle[chave] = agora
        return True

    # ── persistência best-effort ──────────────────────────────────────────

    def _registrar_banco(self, chave: str, nivel: str, mensagem: str, enviado: bool) -> None:
        try:
            executar_comando(
                "INSERT INTO alert_log (chave, nivel, mensagem, canal, enviado, ts) "
                "VALUES (:chave, :nivel, :mensagem, 'webhook', :enviado, NOW())",
                {"chave": chave, "nivel": nivel, "mensagem": mensagem, "enviado": enviado},
            )
        except Exception as e:
            self._log.debug(f"Falha ao registrar alerta no banco: {e}")

    # ── dead letter queue (DLQ) ────────────────────────────────────────────

    def _dlq_loop(self) -> None:
        while True:
            time.sleep(300)
            self._flush_dlq()

    def _flush_dlq(self) -> None:
        with self._dlq_lock:
            pendentes = list(self._dlq)
            self._dlq.clear()
        reenviados = 0
        for item in pendentes:
            if self._post_teams(item["msg"]):
                reenviados += 1
            else:
                with self._dlq_lock:
                    self._dlq.append(item)
        if reenviados:
            self._log.info(f"[DLQ] {reenviados} mensagem(ns) reenviada(s).")

    @property
    def dlq_size(self) -> int:
        return len(self._dlq)

    # ── Teams ──────────────────────────────────────────────────────────────

    def _post_teams(self, mensagem: str) -> bool:
        if not CFG.TEAMS_WEBHOOK:
            return True
        try:
            r = requests.post(CFG.TEAMS_WEBHOOK, json={"text": mensagem}, timeout=10)
            return r.status_code < 400
        except Exception:
            return False

    def enviar_teams(
        self,
        mensagem: str,
        nivel: str = "INFO",
        chave: str = "geral",
        throttle_seg: Optional[int] = None,
        forcar: bool = False,
    ) -> bool:
        if not forcar and not self._pode_enviar(chave, throttle_seg):
            return False

        icone = ICONES_ALERTA.get(nivel.upper(), "📢")
        texto = f"{icone} **[{nivel.upper()}]** {mensagem}"
        ok = self._post_teams(texto)
        self._registrar_banco(chave, nivel, mensagem, ok)

        if ok:
            self._log.info(f"Teams OK: chave={chave} nivel={nivel}")
        else:
            self._log.warning(f"Teams falhou: chave={chave} → DLQ")
            with self._dlq_lock:
                self._dlq.append({"msg": texto, "chave": chave, "ts": datetime.utcnow().isoformat()})
        return ok

    # ── Email ──────────────────────────────────────────────────────────────

    def enviar_email(self, assunto: str, corpo: str, anexo_path: Optional[str] = None) -> None:
        import os

        if not CFG.EMAIL_SENHA or not CFG.EMAIL_DESTINOS_LIST:
            self._log.warning("Email não configurado — pulando envio.")
            return
        try:
            msg = MIMEMultipart()
            msg["From"] = CFG.EMAIL_USER
            msg["To"] = ", ".join(CFG.EMAIL_DESTINOS_LIST)
            msg["Subject"] = assunto
            msg.attach(MIMEText(corpo, "html"))
            if anexo_path and os.path.exists(anexo_path):
                with open(anexo_path, "rb") as fh:
                    parte = MIMEBase("application", "octet-stream")
                    parte.set_payload(fh.read())
                encoders.encode_base64(parte)
                parte.add_header(
                    "Content-Disposition",
                    f"attachment; filename={os.path.basename(anexo_path)}",
                )
                msg.attach(parte)
            with smtplib.SMTP(CFG.EMAIL_SMTP, CFG.EMAIL_PORTA) as srv:
                srv.starttls()
                srv.login(CFG.EMAIL_USER, CFG.EMAIL_SENHA)
                srv.sendmail(CFG.EMAIL_USER, CFG.EMAIL_DESTINOS_LIST, msg.as_string())
            self._log.info(f"Email enviado: {assunto}")
        except Exception as e:
            self._log.error(f"Falha email: {e}")


ALERTAS = GestorAlertas()


def send_webhook_alert(
    mensagem: str,
    nivel: str = "INFO",
    chave: str = "geral",
    throttle_seg: Optional[int] = None,
    forcar: bool = False,
) -> bool:
    """Atalho funcional equivalente a ALERTAS.enviar_teams(...)."""
    return ALERTAS.enviar_teams(mensagem, nivel=nivel, chave=chave, throttle_seg=throttle_seg, forcar=forcar)
