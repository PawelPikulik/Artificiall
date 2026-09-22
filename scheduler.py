"""Scheduled report runner using APScheduler.

Stretch feature for BE-08: generate reports on a recurring schedule.
Integrates with FastAPI lifespan events to start/stop the scheduler.
"""

import os
from datetime import datetime

from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger

import db
import jobs

scheduler: BackgroundScheduler | None = None


def get_scheduler() -> BackgroundScheduler:
    """Return the global scheduler instance, initializing if needed."""
    global scheduler
    if scheduler is None:
        scheduler = BackgroundScheduler()
    return scheduler


def start_scheduler():
    """Start the background scheduler and reload active scheduled reports."""
    sched = get_scheduler()
    if not sched.running:
        _reload_scheduled_jobs()
        sched.start()


def stop_scheduler():
    """Shutdown the scheduler cleanly."""
    global scheduler
    if scheduler and scheduler.running:
        scheduler.shutdown(wait=False)
        scheduler = None


def _reload_scheduled_jobs():
    """Load all active scheduled reports from the DB and register them."""
    sched = get_scheduler()
    # Remove existing report jobs to avoid duplicates
    for job in sched.get_jobs():
        if job.id.startswith("scheduled_report_"):
            sched.remove_job(job.id)

    scheduled = db.list_scheduled_reports()
    for s in scheduled:
        if not s["active"]:
            continue
        job_id = f"scheduled_report_{s['id']}"
        sched.add_job(
            _run_scheduled_report,
            trigger=CronTrigger.from_crontab(s["schedule_cron"]),
            id=job_id,
            replace_existing=True,
            args=[s["id"], s["report_type"], s["user_id"]],
        )


def _run_scheduled_report(scheduled_id: int, report_type: str, user_id: str):
    """Create a new report record and kick off background generation."""
    report = db.create_report(
        report_type=report_type,
        user_id=user_id,
        metadata={"scheduled_from": scheduled_id, "triggered_at": datetime.now().isoformat()},
    )
    jobs.run_report_job(report["id"], report_type)


def add_scheduled_job(report_type: str, cron: str, user_id: str = "", metadata: dict = None) -> dict:
    """Persist a scheduled report and register it with the scheduler."""
    scheduled = db.create_scheduled_report(
        report_type=report_type,
        schedule_cron=cron,
        user_id=user_id,
        metadata=metadata or {},
    )
    job_id = f"scheduled_report_{scheduled['id']}"
    get_scheduler().add_job(
        _run_scheduled_report,
        trigger=CronTrigger.from_crontab(cron),
        id=job_id,
        replace_existing=True,
        args=[scheduled["id"], report_type, user_id],
    )
    return scheduled


def remove_scheduled_job(scheduled_id: int):
    """Deactivate a scheduled report and remove it from the scheduler."""
    db.update_scheduled_report_active(scheduled_id, False)
    job_id = f"scheduled_report_{scheduled_id}"
    sched = get_scheduler()
    try:
        sched.remove_job(job_id)
    except Exception:
        pass  # Job may not exist in scheduler
