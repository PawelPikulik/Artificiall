from fastapi import FastAPI, HTTPException, Request, Query
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field
from typing import Optional

import db

app = FastAPI(
    title="Task API",
    version="1.0.0",
    description="A simple CRUD API for managing tasks.",
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


@app.get("/", summary="API Info")
def read_root():
    """Return API metadata."""
    return {
        "name": "Task API",
        "version": "1.0",
        "endpoints": ["/tasks"],
    }


@app.get("/health", summary="Health Check")
def health_check():
    """Check if the server is alive."""
    return {"status": "ok"}


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
