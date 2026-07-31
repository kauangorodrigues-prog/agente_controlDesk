from __future__ import annotations

import json
import threading
from datetime import datetime
from http.server import BaseHTTPRequestHandler, HTTPServer
from typing import Optional

from .alerts import ALERTAS
from .clients import EasyClient, OlosClient
from .config import CFG
from .db import testar_conexao
from .logging_setup import get_logger

log = get_logger("health")


def status_saude() -> dict:
    return {
        "versao": "3.0.0",
        "ts": datetime.now().isoformat(),
        "banco_ok": testar_conexao(),
        "dlq_size": ALERTAS.dlq_size,
        "circuito_olos_aberto": OlosClient.circuito_aberto(),
        "circuito_easy_aberto": EasyClient.circuito_aberto(),
    }


class _Handler(BaseHTTPRequestHandler):
    def do_GET(self) -> None:
        if self.path == "/health":
            payload = json.dumps(status_saude(), indent=2, default=str).encode()
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            self.wfile.write(payload)
        else:
            self.send_response(404)
            self.end_headers()

    def log_message(self, *args) -> None:
        pass  # silencia logs de acesso HTTP no console


def iniciar_health_check(porta: Optional[int] = None) -> None:
    porta = porta or CFG.HEALTH_PORT
    try:
        server = HTTPServer(("0.0.0.0", porta), _Handler)
        threading.Thread(target=server.serve_forever, daemon=True, name="health-check").start()
        log.info(f"Health check: http://localhost:{porta}/health")
    except OSError as e:
        log.warning(f"Não foi possível iniciar health check: {e}")
