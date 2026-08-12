"""
Task API — AI-generated version (Stage 7 rematch).
A simple FastAPI CRUD application for managing to-do tasks in memory.
"""

from fastapi import FastAPI, HTTPException, Query
from pydantic import BaseModel, Field, validator
from typing import Optional, List

app = FastAPI(
    title="Task API",
    description="A simple to-do task API with in-memory storage.",
    version="1.0.0",
)


# ---------------------------------------------------------------------------
# In-memory storage
# ---------------------------------------------------------------------------
_task_counter = 3  # highest id used so far
_tasks_db: List[dict] = [
    {"id": 1, "title": "Buy groceries", "done": False},
    {"id": 2, "title": "Walk the dog", "done": True},
    {"id": 3, "title": "Read a book", "done": False},
]


def _find_task(task_id: int) -> Optional[dict]:
    """Return the task dict or None if not found."""
    return next((t for t in _tasks_db if t["id"] == task_id), None)


def _remove_task(task_id: int) -> bool:
    """Remove a task by id. Return True if found and removed."""
    for idx, t in enumerate(_tasks_db):
        if t["id"] == task_id:
            _tasks_db.pop(idx)
            return True
    return False


# ---------------------------------------------------------------------------
# Pydantic models
# ---------------------------------------------------------------------------
class TaskCreate(BaseModel):
    title: str = Field(..., description="The task title")
    done: bool = Field(False, description="Whether the task is completed")

    @validator("title")
    def title_must_not_be_empty(cls, v: str) -> str:
        if not v or not v.strip():
            raise ValueError("Title is required and cannot be empty")
        return v.strip()


class TaskUpdate(BaseModel):
    title: Optional[str] = Field(None, description="The task title")
    done: Optional[bool] = Field(None, description="Whether the task is completed")

    @validator("title")
    def title_must_not_be_empty_when_provided(cls, v: Optional[str]) -> Optional[str]:
        if v is not None and not v.strip():
            raise ValueError("Title cannot be empty")
        return v.strip() if v is not None else v


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------
@app.get("/", summary="API metadata")
async def root():
    """Return basic API information."""
    return {"name": "Task API", "version": "1.0", "endpoints": ["/tasks"]}


@app.get("/health", summary="Health check")
async def health():
    """Check if the server is running."""
    return {"status": "ok"}


@app.get("/tasks", summary="List all tasks")
async def list_tasks(
    done: Optional[bool] = Query(None, description="Filter by completion status"),
    search: Optional[str] = Query(None, description="Search in titles (case-insensitive)"),
):
    """Return all tasks, with optional filtering and search."""
    results = _tasks_db.copy()
    if done is not None:
        results = [t for t in results if t["done"] == done]
    if search:
        q = search.lower()
        results = [t for t in results if q in t["title"].lower()]
    return results


@app.get("/tasks/{task_id}", summary="Get a single task")
async def get_task(task_id: int):
    """Return a task by its numeric id."""
    task = _find_task(task_id)
    if task is None:
        raise HTTPException(status_code=404, detail=f"Task {task_id} not found")
    return task


@app.post("/tasks", status_code=201, summary="Create a new task")
async def create_task(data: TaskCreate):
    """Add a new task to the list."""
    global _task_counter
    _task_counter += 1
    new_task = {"id": _task_counter, "title": data.title, "done": data.done}
    _tasks_db.append(new_task)
    return new_task


@app.put("/tasks/{task_id}", summary="Update an existing task")
async def update_task(task_id: int, data: TaskUpdate):
    """Modify a task's title and/or completion status."""
    task = _find_task(task_id)
    if task is None:
        raise HTTPException(status_code=404, detail=f"Task {task_id} not found")
    if data.title is not None:
        task["title"] = data.title
    if data.done is not None:
        task["done"] = data.done
    return task


@app.delete("/tasks/{task_id}", status_code=204, summary="Delete a task")
async def delete_task(task_id: int):
    """Remove a task permanently."""
    if not _remove_task(task_id):
        raise HTTPException(status_code=404, detail=f"Task {task_id} not found")
    return None


@app.get("/stats", summary="Task statistics")
async def stats():
    """Return counts of total, done, and open tasks."""
    total = len(_tasks_db)
    done = sum(1 for t in _tasks_db if t["done"])
    return {"total": total, "done": done, "open": total - done}


@app.post("/reset", summary="Reset tasks")
async def reset():
    """Restore the original 3 example tasks."""
    global _task_counter
    _task_counter = 3
    _tasks_db.clear()
    _tasks_db.extend([
        {"id": 1, "title": "Buy groceries", "done": False},
        {"id": 2, "title": "Walk the dog", "done": True},
        {"id": 3, "title": "Read a book", "done": False},
    ])
    return _tasks_db
