from fastapi import FastAPI, HTTPException, Request, Query
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field
from typing import Optional

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


# In-memory task storage
tasks = [
    {"id": 1, "title": "Buy groceries", "done": False},
    {"id": 2, "title": "Walk the dog", "done": True},
    {"id": 3, "title": "Read a book", "done": False},
]


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
    result = tasks
    if done is not None:
        result = [t for t in result if t["done"] == done]
    if search:
        result = [t for t in result if search.lower() in t["title"].lower()]
    return result


@app.get("/tasks/{task_id}", summary="Get a Single Task")
def get_task(task_id: int):
    """Get a single task by its ID."""
    for task in tasks:
        if task["id"] == task_id:
            return task
    raise HTTPException(status_code=404, detail=f"Task {task_id} not found")


@app.post("/tasks", status_code=201, summary="Create a Task")
def create_task(payload: TaskCreate):
    """Create a new task. Returns 201 Created."""
    new_id = max((t["id"] for t in tasks), default=0) + 1
    task = {
        "id": new_id,
        "title": payload.title,
        "done": payload.done if payload.done is not None else False,
    }
    tasks.append(task)
    return task


@app.put("/tasks/{task_id}", summary="Update a Task")
def update_task(task_id: int, payload: TaskUpdate):
    """Replace a task's title and/or done status."""
    for task in tasks:
        if task["id"] == task_id:
            if payload.title is not None:
                task["title"] = payload.title
            if payload.done is not None:
                task["done"] = payload.done
            return task
    raise HTTPException(status_code=404, detail=f"Task {task_id} not found")


@app.delete("/tasks/{task_id}", status_code=204, summary="Delete a Task")
def delete_task(task_id: int):
    """Remove a task by its ID. Returns 204 No Content."""
    for idx, task in enumerate(tasks):
        if task["id"] == task_id:
            tasks.pop(idx)
            return None
    raise HTTPException(status_code=404, detail=f"Task {task_id} not found")


@app.get("/stats", summary="Task Statistics")
def get_stats():
    """Return statistics about the task list."""
    total = len(tasks)
    done_count = sum(1 for t in tasks if t["done"])
    return {"total": total, "done": done_count, "open": total - done_count}


@app.post("/reset", status_code=200, summary="Reset Tasks")
def reset_tasks():
    """Reset the task list to the initial 3 example tasks."""
    tasks.clear()
    tasks.extend([
        {"id": 1, "title": "Buy groceries", "done": False},
        {"id": 2, "title": "Walk the dog", "done": True},
        {"id": 3, "title": "Read a book", "done": False},
    ])
    return tasks
