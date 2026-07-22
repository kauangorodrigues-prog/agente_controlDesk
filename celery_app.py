"""Worker Celery opcional (Fase 3 — filas).

Só é usado quando CELERY_BROKER_URL está definido; caso contrário, a aplicação
usa a fila de prioridade em processo (sem broker externo). O broker pode ser
Redis ou RabbitMQ — basta trocar a URL.

Subir o worker:
    celery -A celery_app worker --loglevel=INFO
"""
from __future__ import annotations

import os

from celery import Celery

_broker = os.getenv("CELERY_BROKER_URL", "redis://localhost:6379/0")
_backend = os.getenv("CELERY_RESULT_BACKEND", "") or None

app = Celery("control_desk", broker=_broker, backend=_backend)
app.conf.update(
    task_default_queue="celery",
    task_acks_late=True,
    worker_prefetch_multiplier=1,
    task_default_priority=2,
)


@app.task(name="executar_job")
def executar_job(nome: str):
    """Executa um job do registro reutilizando o wrapper resiliente _safe_run."""
    # Import tardio para evitar ciclo e custo no boot do worker.
    from agente_ia_control_desk import JOBS_REGISTRO, _safe_run

    fn = JOBS_REGISTRO.get(nome)
    if not fn:
        raise ValueError(f"job desconhecido: {nome}")
    _safe_run(fn, nome)
    return {"job": nome, "status": "ok"}
