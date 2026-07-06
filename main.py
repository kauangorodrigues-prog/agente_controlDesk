"""Entrypoint do Agente IA Control Desk.

Uso:
    python main.py                    # modo standalone: scheduler + health check HTTP (:8080/health)
    python main.py api [porta]        # API FastAPI completa via uvicorn (:8000 por padrão, docs em /docs)
    python main.py alo [porta]        # robô Analisador de Ligações ALO / NÃO ALO (:5501 por padrão)
    streamlit run dashboard_app.py    # dashboard Streamlit
"""
from __future__ import annotations

import os
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


def _porta(indice: int, env: str, padrao: int) -> int:
    if len(sys.argv) > indice:
        try:
            return int(sys.argv[indice])
        except ValueError:
            pass
    return int(os.getenv(env, str(padrao)))


def rodar_api() -> None:
    import uvicorn
    porta = _porta(2, "API_PORT", 8000)
    log.info(f"🚀 API Control Desk em http://0.0.0.0:{porta} (docs em /docs)")
    uvicorn.run("control_desk.api:app", host="0.0.0.0", port=porta, reload=False)


def rodar_robo_alo() -> None:
    from control_desk.alo_server import run
    run(port=_porta(2, "ROBO_ALO_PORT", 5501))


if __name__ == "__main__":
    gerar_env_example()
    modo = sys.argv[1] if len(sys.argv) > 1 else ""
    if modo == "api":
        rodar_api()
    elif modo == "alo":
        rodar_robo_alo()
    else:
        rodar_standalone()
