"""Background worker for AI task analysis.

Moves the slow LLM call out of the HTTP request path.
Features:
- Idempotency: same-task jobs reuse existing completed results
- Retry logic: exponential backoff on transient failures
- Failure alerting: detailed error logging in the job record
- FastAPI BackgroundTasks integration
"""

import traceback
import time
from typing import Optional

import db
import llm


def _is_terminal_status(status: str) -> bool:
    return status in ("completed", "failed")


def find_or_create_job(task_id: int, max_attempts: int = 3) -> dict:
    """Idempotency gate: return an existing completed/running job for this task
    if one exists, otherwise create a new pending job.
    """
    existing = db.find_latest_job_for_task(task_id, job_type="task_analysis")
    if existing and _is_terminal_status(existing["status"]):
        # Reuse completed or failed result — do not duplicate work
        return existing
    if existing and existing["status"] == "running":
        # Already in progress — return the same job
        return existing
    return db.create_job(task_id=task_id, job_type="task_analysis", max_attempts=max_attempts)


def _do_analysis(task_id: int) -> dict:
    """Synchronous work: fetch task, call LLM, return structured result."""
    task = db.get_task(task_id)
    if task is None:
        raise ValueError(f"Task {task_id} not found")
    analysis = llm.analyze_task(task["title"])
    return {
        "task_id": task_id,
        "title": task["title"],
        "analysis": analysis.model_dump(),
    }


def run_analysis_job(job_id: int):
    """Execute an analysis job with retries and idempotency.

    Meant to be handed off to FastAPI BackgroundTasks.
    """
    job = db.get_job(job_id)
    if job is None:
        raise ValueError(f"Job {job_id} not found")

    # Short-circuit if already terminal (idempotency)
    if _is_terminal_status(job["status"]):
        return

    db.update_job_status(job_id, "running", attempts=job["attempts"] + 1)

    max_attempts = job.get("max_attempts", 3)
    base_delay = 1.0
    last_error: Optional[str] = None

    for attempt in range(1, max_attempts + 1):
        try:
            result = _do_analysis(job["task_id"])
            db.update_job_status(job_id, "completed", result=result)
            return
        except Exception as exc:
            last_error = f"Attempt {attempt}/{max_attempts}: {exc}\n{traceback.format_exc()}"
            if attempt < max_attempts:
                delay = base_delay * (2 ** (attempt - 1))
                time.sleep(delay)

    # All retries exhausted — mark as failed
    db.update_job_status(job_id, "failed", error_message=last_error)
