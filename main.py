import sqlite3
from fastapi import FastAPI, HTTPException, Request, Query
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field
from typing import Optional

DATABASE = "tasks.db"

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


def get_db():
    conn = sqlite3.connect(DATABASE)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS tasks (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            title TEXT NOT NULL,
            done INTEGER NOT NULL DEFAULT 0
        )
        """
    )
    cursor.execute("SELECT COUNT(*) FROM tasks")
    count = cursor.fetchone()[0]
    if count == 0:
        cursor.executemany(
            "INSERT INTO tasks (title, done) VALUES (?, ?)",
            [
                ("Buy groceries", 0),
                ("Walk the dog", 1),
                ("Read a book", 0),
            ],
        )
        conn.commit()
    conn.close()


@app.on_event("startup")
def on_startup():
    init_db()


def row_to_task(row) -> dict:
    return {"id": row["id"], "title": row["title"], "done": bool(row["done"])}


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
    conn = get_db()
    cursor = conn.cursor()

    query = "SELECT * FROM tasks WHERE 1=1"
    params = []

    if done is not None:
        query += " AND done = ?"
        params.append(1 if done else 0)
    if search:
        query += " AND title LIKE ?"
        params.append(f"%{search}%")

    query += " ORDER BY id"
    cursor.execute(query, params)
    rows = cursor.fetchall()
    conn.close()
    return [row_to_task(row) for row in rows]


@app.get("/tasks/{task_id}", summary="Get a Single Task")
def get_task(task_id: int):
    """Get a single task by its ID."""
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM tasks WHERE id = ?", (task_id,))
    row = cursor.fetchone()
    conn.close()
    if row is None:
        raise HTTPException(status_code=404, detail=f"Task {task_id} not found")
    return row_to_task(row)


@app.post("/tasks", status_code=201, summary="Create a Task")
def create_task(payload: TaskCreate):
    """Create a new task. Returns 201 Created."""
    conn = get_db()
    cursor = conn.cursor()
    done_val = 1 if payload.done else 0
    cursor.execute(
        "INSERT INTO tasks (title, done) VALUES (?, ?)",
        (payload.title, done_val),
    )
    conn.commit()
    new_id = cursor.lastrowid
    conn.close()
    return {
        "id": new_id,
        "title": payload.title,
        "done": payload.done if payload.done is not None else False,
    }


@app.put("/tasks/{task_id}", summary="Update a Task")
def update_task(task_id: int, payload: TaskUpdate):
    """Replace a task's title and/or done status."""
    conn = get_db()
    cursor = conn.cursor()

    cursor.execute("SELECT * FROM tasks WHERE id = ?", (task_id,))
    row = cursor.fetchone()
    if row is None:
        conn.close()
        raise HTTPException(status_code=404, detail=f"Task {task_id} not found")

    updates = []
    params = []
    if payload.title is not None:
        updates.append("title = ?")
        params.append(payload.title)
    if payload.done is not None:
        updates.append("done = ?")
        params.append(1 if payload.done else 0)

    if updates:
        query = f"UPDATE tasks SET {', '.join(updates)} WHERE id = ?"
        params.append(task_id)
        cursor.execute(query, params)
        conn.commit()

    cursor.execute("SELECT * FROM tasks WHERE id = ?", (task_id,))
    row = cursor.fetchone()
    conn.close()
    return row_to_task(row)


@app.delete("/tasks/{task_id}", status_code=204, summary="Delete a Task")
def delete_task(task_id: int):
    """Remove a task by its ID. Returns 204 No Content."""
    conn = get_db()
    cursor = conn.cursor()

    cursor.execute("SELECT * FROM tasks WHERE id = ?", (task_id,))
    row = cursor.fetchone()
    if row is None:
        conn.close()
        raise HTTPException(status_code=404, detail=f"Task {task_id} not found")

    cursor.execute("DELETE FROM tasks WHERE id = ?", (task_id,))
    conn.commit()
    conn.close()
    return None


@app.get("/stats", summary="Task Statistics")
def get_stats():
    """Return statistics about the task list."""
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("SELECT COUNT(*) FROM tasks")
    total = cursor.fetchone()[0]
    cursor.execute("SELECT COUNT(*) FROM tasks WHERE done = 1")
    done_count = cursor.fetchone()[0]
    conn.close()
    return {"total": total, "done": done_count, "open": total - done_count}


@app.post("/reset", status_code=200, summary="Reset Tasks")
def reset_tasks():
    """Reset the task list to the initial 3 example tasks."""
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("DELETE FROM tasks")
    cursor.executemany(
        "INSERT INTO tasks (title, done) VALUES (?, ?)",
        [
            ("Buy groceries", 0),
            ("Walk the dog", 1),
            ("Read a book", 0),
        ],
    )
    conn.commit()
    cursor.execute("SELECT * FROM tasks ORDER BY id")
    rows = cursor.fetchall()
    conn.close()
    return [row_to_task(row) for row in rows]
