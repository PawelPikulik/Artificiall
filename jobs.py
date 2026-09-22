"""Background job runner for PDF report generation.

Uses FastAPI BackgroundTasks for on-demand async execution.
Queries data, generates PDF, updates report status, and handles errors gracefully.
"""

import traceback
from pathlib import Path

import db
import report_generator


def run_report_job(report_id: int, report_type: str):
    """Execute a report generation job synchronously.

    This function is meant to be handed off to FastAPI BackgroundTasks.
    It updates the report record from pending → running → completed/failed.

    Args:
        report_id: The DB report ID to process.
        report_type: The report type key (e.g. 'task_summary', 'book_catalog').
    """
    try:
        # Mark as running
        db.update_report_status(report_id, "running")

        # Generate PDF
        file_path = report_generator.generate_report(report_id, report_type)

        # Mark as completed
        db.update_report_status(report_id, "completed", file_path=file_path)

    except Exception as exc:
        error_msg = f"{exc}\n{traceback.format_exc()}"
        db.update_report_status(report_id, "failed", error_message=error_msg)


def cleanup_report_file(report_id: int):
    """Remove the PDF file associated with a report, if it exists."""
    report = db.get_report(report_id)
    if report and report.get("file_path"):
        path = Path(report["file_path"])
        if path.exists():
            path.unlink()
