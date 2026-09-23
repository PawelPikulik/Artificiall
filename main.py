from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException, Request, Query, Depends, BackgroundTasks
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse, FileResponse
from pydantic import BaseModel, Field
from typing import Optional

import db
import auth
import llm
import jobs
import scheduler as sched
import analysis_worker

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Start the report scheduler on startup and shut it down on exit."""
    sched.start_scheduler()
    yield
    sched.stop_scheduler()


app = FastAPI(
    title="Task API",
    version="2.0.0",
    description="A secure CRUD API for managing tasks with Supabase authentication, plus PDF report generation.",
    lifespan=lifespan,
)



@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    return JSONResponse(
        status_code=400,
        content={"error": "Invalid request body"},
    )


class TaskCreate(BaseModel):
    title: str = Field(..., min_length=1, description="The task title")
    done: Optional[bool] = Field(False, description="Whether the task is completed")


class TaskUpdate(BaseModel):
    title: Optional[str] = Field(None, min_length=1, description="The task title")
    done: Optional[bool] = Field(None, description="Whether the task is completed")


class SignupRequest(BaseModel):
    email: str = Field(..., description="User email")
    password: str = Field(..., min_length=6, description="User password")


class LoginRequest(BaseModel):
    email: str = Field(..., description="User email")
    password: str = Field(..., description="User password")


class TaskAnalysisResponse(BaseModel):
    task_id: int = Field(..., description="ID of the analyzed task")
    title: str = Field(..., description="Task title")
    analysis: llm.TaskAnalysis = Field(..., description="AI-generated structured analysis")


class JobStatusResponse(BaseModel):
    id: int = Field(..., description="Job ID")
    task_id: int = Field(..., description="Task ID")
    status: str = Field(..., description="pending | running | completed | failed")
    result: Optional[dict] = Field(None, description="Structured analysis result when completed")
    error_message: Optional[str] = Field(None, description="Error details when failed")
    attempts: int = Field(..., description="Number of execution attempts")
    max_attempts: int = Field(..., description="Maximum retry attempts")
    created_at: Optional[str] = Field(None, description="ISO timestamp when job was created")
    completed_at: Optional[str] = Field(None, description="ISO timestamp when job finished")


class ReportCreate(BaseModel):
    report_type: str = Field(..., pattern=r"^(task_summary|book_catalog)$", description="Report type")


class ReportScheduleCreate(BaseModel):
    report_type: str = Field(..., pattern=r"^(task_summary|book_catalog)$", description="Report type")
    cron: str = Field(..., min_length=1, description="Cron expression, e.g. '0 9 * * 1' for Mondays at 9am")


@app.get("/", summary="API Info")
def read_root():
    """Return API metadata."""
    return {
        "name": "Task API",
        "version": "2.0",
        "endpoints": ["/tasks", "/auth", "/public", "/protected"],
    }


@app.get("/health", summary="Health Check")
def health_check():
    """Check if the server is alive."""
    return {"status": "ok"}


# ------------------------------------------------------------------
# Auth routes
# ------------------------------------------------------------------

@app.post("/auth/signup", status_code=201, summary="Sign Up")
def signup(payload: SignupRequest):
    """Create a new user account via Supabase Auth."""
    try:
        response = auth.sign_up(payload.email, payload.password)
        user = response.user
        # Dev-only: auto-confirm user if SUPABASE_SERVICE_KEY is set
        auth.confirm_user(user.id)
        return {
            "id": user.id,
            "email": user.email,
            "created_at": user.created_at,
        }
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@app.post("/auth/login", summary="Log In")
def login(payload: LoginRequest):
    """Authenticate user and return JWT tokens."""
    try:
        response = auth.sign_in(payload.email, payload.password)
        if response.session is None:
            raise HTTPException(status_code=401, detail="Invalid login credentials")
        user = response.user
        return {
            "access_token": response.session.access_token,
            "refresh_token": response.session.refresh_token,
            "user": {
                "id": user.id,
                "email": user.email,
                "created_at": user.created_at,
            },
        }
    except Exception as e:
        raise HTTPException(status_code=401, detail="Invalid login credentials")


@app.post("/auth/logout", status_code=204, summary="Log Out", dependencies=[Depends(auth.get_current_user)])
def logout(credentials=Depends(auth.security)):
    """Terminate the user session. Requires Bearer token."""
    token = credentials.credentials
    auth.sign_out(token)
    return None


@app.get("/public/info", summary="Public Info")
def public_info():
    """Public endpoint that requires no authentication."""
    return {"message": "Welcome stranger! This info is public."}


@app.get("/protected/profile", summary="Protected Profile", dependencies=[Depends(auth.get_current_user)])
def protected_profile(user=Depends(auth.get_current_user)):
    """Read private user profile data. Requires Bearer token."""
    return {
        "id": user.id,
        "email": user.email,
        "created_at": user.created_at,
    }


@app.get("/tasks", summary="List Tasks")
def list_tasks(
    done: Optional[bool] = Query(None, description="Filter by completion status"),
    search: Optional[str] = Query(None, description="Search in task titles"),
):
    """List all tasks, optionally filtered by status or search query."""
    return db.list_tasks(done=done, search=search)


@app.get("/tasks/{task_id}", summary="Get a Single Task")
def get_task(task_id: int):
    """Get a single task by its ID."""
    task = db.get_task(task_id)
    if task is None:
        raise HTTPException(status_code=404, detail=f"Task {task_id} not found")
    return task


@app.post("/tasks", status_code=201, summary="Create a Task")
def create_task(payload: TaskCreate):
    """Create a new task. Returns 201 Created."""
    done_val = payload.done if payload.done is not None else False
    return db.create_task(title=payload.title, done=done_val)


@app.put("/tasks/{task_id}", summary="Update a Task")
def update_task(task_id: int, payload: TaskUpdate):
    """Replace a task's title and/or done status."""
    task = db.update_task(
        task_id,
        title=payload.title,
        done=payload.done,
    )
    if task is None:
        raise HTTPException(status_code=404, detail=f"Task {task_id} not found")
    return task


@app.delete("/tasks/{task_id}", status_code=204, summary="Delete a Task")
def delete_task(task_id: int):
    """Remove a task by its ID. Returns 204 No Content."""
    result = db.delete_task(task_id)
    if result is None:
        raise HTTPException(status_code=404, detail=f"Task {task_id} not found")
    return None


@app.get("/stats", summary="Task Statistics")
def get_stats():
    """Return statistics about the task list."""
    return db.get_stats()


@app.post("/reset", status_code=200, summary="Reset Tasks")
def reset_tasks():
    """Reset the task list to the initial 3 example tasks."""
    return db.reset_tasks()


@app.post("/tasks/{task_id}/analyze", status_code=202, summary="Queue AI Task Analysis")
def analyze_task_endpoint(task_id: int, background_tasks: BackgroundTasks):
    """Queue an LLM analysis of a task. Returns 202 Accepted immediately.

    The actual analysis runs in the background. Poll GET /jobs/{job_id} for status.
    If a completed or running job already exists for this task, it is reused
    (idempotency — no duplicate work).
    """
    task = db.get_task(task_id)
    if task is None:
        raise HTTPException(status_code=404, detail=f"Task {task_id} not found")

    job = analysis_worker.find_or_create_job(task_id, max_attempts=3)

    # Only enqueue if the job is fresh (pending) or we created a new one
    if job["status"] == "pending":
        background_tasks.add_task(analysis_worker.run_analysis_job, job["id"])

    return {
        "job_id": job["id"],
        "status": job["status"],
        "status_url": f"/jobs/{job['id']}",
        "message": "Analysis queued. Poll status_url for progress.",
    }


@app.get("/jobs/{job_id}", status_code=200, summary="Get Job Status")
def get_job_status(job_id: int):
    """Check the status of a background analysis job.

    Returns the full result when completed, or error details when failed.
    """
    job = db.get_job(job_id)
    if job is None:
        raise HTTPException(status_code=404, detail=f"Job {job_id} not found")
    return JobStatusResponse(
        id=job["id"],
        task_id=job["task_id"],
        status=job["status"],
        result=job.get("result"),
        error_message=job.get("error_message"),
        attempts=job["attempts"],
        max_attempts=job["max_attempts"],
        created_at=job.get("created_at"),
        completed_at=job.get("completed_at"),
    )


@app.get("/tasks/{task_id}/analysis", status_code=200, summary="Get Task Analysis Result")
def get_task_analysis(task_id: int):
    """Shortcut: get the latest completed analysis result for a task.

    Returns 404 if the task has never been analyzed.
    """
    task = db.get_task(task_id)
    if task is None:
        raise HTTPException(status_code=404, detail=f"Task {task_id} not found")

    job = db.find_latest_job_for_task(task_id, job_type="task_analysis")
    if job is None:
        raise HTTPException(status_code=404, detail=f"Task {task_id} has not been analyzed yet. POST /tasks/{task_id}/analyze to start.")
    if job["status"] != "completed":
        raise HTTPException(status_code=409, detail=f"Analysis is {job['status']}. Check /jobs/{job['id']} for progress.")

    return TaskAnalysisResponse(
        task_id=task_id,
        title=task["title"],
        analysis=llm.TaskAnalysis(**job["result"]["analysis"]),
    )


# ------------------------------------------------------------------
# Report routes
# ------------------------------------------------------------------

@app.post("/reports", status_code=202, summary="Generate a Report", dependencies=[Depends(auth.get_current_user)])
def create_report(payload: ReportCreate, background_tasks: BackgroundTasks, user=Depends(auth.get_current_user)):
    """Queue a PDF report generation job. Returns immediately with a job ID.

    The actual generation runs in the background; poll GET /reports/{id} for status.
    """
    report = db.create_report(report_type=payload.report_type, user_id=user.id)
    background_tasks.add_task(jobs.run_report_job, report["id"], payload.report_type)
    return {
        "id": report["id"],
        "status": report["status"],
        "report_type": report["report_type"],
        "download_url": f"/reports/{report['id']}/download",
    }


@app.get("/reports", summary="List Reports", dependencies=[Depends(auth.get_current_user)])
def list_reports(user=Depends(auth.get_current_user)):
    """List all reports for the authenticated user."""
    return db.list_reports(user_id=user.id)


@app.get("/reports/{report_id}", summary="Get Report Status", dependencies=[Depends(auth.get_current_user)])
def get_report(report_id: int, user=Depends(auth.get_current_user)):
    """Get a single report's status and metadata."""
    report = db.get_report(report_id, user_id=user.id)
    if report is None:
        raise HTTPException(status_code=404, detail=f"Report {report_id} not found")
    return report


@app.get("/reports/{report_id}/download", summary="Download Report PDF", dependencies=[Depends(auth.get_current_user)])
def download_report(report_id: int, user=Depends(auth.get_current_user)):
    """Stream the generated PDF file. Returns 404 if the report is not yet completed."""
    report = db.get_report(report_id, user_id=user.id)
    if report is None:
        raise HTTPException(status_code=404, detail=f"Report {report_id} not found")
    if report["status"] != "completed":
        raise HTTPException(status_code=409, detail=f"Report is {report['status']}; try again when completed.")
    if not report.get("file_path"):
        raise HTTPException(status_code=500, detail="Report completed but file path is missing.")
    return FileResponse(report["file_path"], media_type="application/pdf", filename=f"report_{report_id}.pdf")


@app.delete("/reports/{report_id}", status_code=204, summary="Delete a Report", dependencies=[Depends(auth.get_current_user)])
def delete_report(report_id: int, user=Depends(auth.get_current_user)):
    """Remove a report and its PDF file."""
    report = db.get_report(report_id, user_id=user.id)
    if report is None:
        raise HTTPException(status_code=404, detail=f"Report {report_id} not found")
    jobs.cleanup_report_file(report_id)
    db.delete_report(report_id, user_id=user.id)
    return None


# ------------------------------------------------------------------
# Scheduled report routes (stretch)
# ------------------------------------------------------------------

@app.post("/reports/schedule", status_code=201, summary="Schedule a Recurring Report", dependencies=[Depends(auth.get_current_user)])
def schedule_report(payload: ReportScheduleCreate, user=Depends(auth.get_current_user)):
    """Create a recurring scheduled report job using a cron expression."""
    scheduled = sched.add_scheduled_job(
        report_type=payload.report_type,
        cron=payload.cron,
        user_id=user.id,
    )
    return scheduled


@app.get("/reports/schedule", summary="List Scheduled Reports", dependencies=[Depends(auth.get_current_user)])
def list_scheduled_reports(user=Depends(auth.get_current_user)):
    """List all recurring scheduled reports for the authenticated user."""
    return db.list_scheduled_reports(user_id=user.id)


@app.delete("/reports/schedule/{scheduled_id}", status_code=204, summary="Cancel a Scheduled Report", dependencies=[Depends(auth.get_current_user)])
def cancel_scheduled_report(scheduled_id: int, user=Depends(auth.get_current_user)):
    """Deactivate a scheduled report and remove it from the scheduler."""
    scheduled = db.get_scheduled_report(scheduled_id, user_id=user.id)
    if scheduled is None:
        raise HTTPException(status_code=404, detail=f"Scheduled report {scheduled_id} not found")
    sched.remove_scheduled_job(scheduled_id)
    return None
