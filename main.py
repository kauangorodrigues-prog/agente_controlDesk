"""Entrypoint do Agente IA Control Desk.

Uso:
    python main.py                    # modo standalone: scheduler + health check HTTP (:8080/health)
    python main.py api                # API FastAPI via uvicorn (:8000, docs em /docs)
    streamlit run dashboard_app.py    # dashboard Streamlit
"""
from __future__ import annotations

import sys
import time

from control_desk.alerts import ALERTAS
from control_desk.config import gerar_env_example
from control_desk.health import iniciar_health_check
from control_desk.logging_setup import get_logger
from control_desk.scheduler import iniciar_scheduler, parar_scheduler

log = get_logger("main")


def rodar_standalone() -> None:
    log.info("🚀 Iniciando Agente IA Control Desk — modo standalone")
    ALERTAS.enviar_teams("🤖 Agente IA Control Desk iniciado.", nivel="INFO", chave="startup", forcar=True)
    iniciar_health_check()
    iniciar_scheduler()
    log.info("Scheduler rodando. Pressione Ctrl+C para encerrar.")
    try:
        while True:
            time.sleep(30)
    except KeyboardInterrupt:
        parar_scheduler()
        log.info("Agente encerrado.")


def rodar_api() -> None:
    import uvicorn
    uvicorn.run("control_desk.api:app", host="0.0.0.0", port=8000, reload=True)


if __name__ == "__main__":
    gerar_env_example()
    if len(sys.argv) > 1 and sys.argv[1] == "api":
        rodar_api()
    else:
        rodar_standalone()
