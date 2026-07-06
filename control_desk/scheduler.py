from __future__ import annotations

import traceback

from .logging_setup import get_logger

log = get_logger("scheduler")

_scheduler = None


def _safe_run(fn, nome: str) -> None:
    try:
        fn()
    except Exception:
        log.error(f"Job '{nome}' falhou:\n{traceback.format_exc()}")


def iniciar_scheduler():
    global _scheduler
    from apscheduler.events import EVENT_JOB_ERROR
    from apscheduler.schedulers.background import BackgroundScheduler
    from apscheduler.triggers.cron import CronTrigger
    from apscheduler.triggers.interval import IntervalTrigger

    from .alo_service import AloService
    from .audit import AuditService
    from .discagem import treinar_async
    from .etl import ETLService
    from .forecast import ForecastService
    from .holidays import HolidayService
    from .mailing import MailingScoreService
    from .occupancy import OccupancyService
    from .pacing import PacingService
    from .reports import ReportService

    _scheduler = BackgroundScheduler(
        job_defaults={"coalesce": True, "max_instances": 1, "misfire_grace_time": 60},
        timezone="America/Sao_Paulo",
    )

    def listener(event):
        if event.exception:
            log.error(f"Job falhou: {event.job_id}")

    _scheduler.add_listener(listener, EVENT_JOB_ERROR)

    _scheduler.add_job(lambda: _safe_run(ETLService.run_etl, "ETL"),
        IntervalTrigger(minutes=5), id="etl")

    _scheduler.add_job(lambda: _safe_run(OccupancyService.calculate_occupancy, "Ocupação"),
        IntervalTrigger(minutes=1), id="ocupacao")

    _scheduler.add_job(lambda: _safe_run(PacingService.auto_adjust_pacing, "Pacing"),
        IntervalTrigger(minutes=2), id="pacing")

    _scheduler.add_job(lambda: _safe_run(lambda: MailingScoreService.calculate_score(), "Mailing"),
        IntervalTrigger(hours=1), id="mailing")

    _scheduler.add_job(lambda: _safe_run(AuditService.run_audit, "Auditoria"),
        IntervalTrigger(minutes=30), id="auditoria")

    _scheduler.add_job(lambda: _safe_run(lambda: AloService.processar_lote(), "AnaliseALO"),
        IntervalTrigger(minutes=15), id="alo")

    _scheduler.add_job(lambda: _safe_run(ReportService.pipeline_intraday, "Relatório"),
        CronTrigger(minute=0), id="relatorio")

    _scheduler.add_job(lambda: _safe_run(lambda: ForecastService.generate_forecast(), "Forecast"),
        CronTrigger(hour="7,13"), id="forecast")

    _scheduler.add_job(lambda: _safe_run(PacingService.retomar_pos_feriado, "Retomada"),
        CronTrigger(hour=7, minute=55), id="retomada_feriado")

    _scheduler.add_job(lambda: _safe_run(
        lambda: HolidayService.sincronizar_feriados_nacionais(), "Feriados"),
        CronTrigger(month=1, day=1, hour=0, minute=5), id="sync_feriados")

    _scheduler.add_job(lambda: _safe_run(treinar_async, "Treino-ML"),
        CronTrigger(hour=2, minute=0), id="treino_ml")

    _scheduler.start()
    log.info(f"{len(_scheduler.get_jobs())} jobs registrados.")


def parar_scheduler():
    global _scheduler
    if _scheduler:
        _scheduler.shutdown(wait=False)
