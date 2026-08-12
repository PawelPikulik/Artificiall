from fastapi import FastAPI, HTTPException, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field
from typing import Optional

app = FastAPI()


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


@app.get("/")
def read_root():
    return {
        "name": "Task API",
        "version": "1.0",
        "endpoints": ["/tasks"],
    }


@app.get("/health")
def health_check():
    return {"status": "ok"}


@app.get("/tasks")
def list_tasks():
    return tasks


@app.get("/tasks/{task_id}")
def get_task(task_id: int):
    for task in tasks:
        if task["id"] == task_id:
            return task
    raise HTTPException(status_code=404, detail=f"Task {task_id} not found")


class TaskUpdate(BaseModel):
    title: Optional[str] = Field(None, min_length=1, description="The task title")
    done: Optional[bool] = Field(None, description="Whether the task is completed")


@app.post("/tasks", status_code=201)
def create_task(payload: TaskCreate):
    new_id = max((t["id"] for t in tasks), default=0) + 1
    task = {
        "id": new_id,
        "title": payload.title,
        "done": payload.done if payload.done is not None else False,
    }
    tasks.append(task)
    return task


@app.put("/tasks/{task_id}")
def update_task(task_id: int, payload: TaskUpdate):
    for task in tasks:
        if task["id"] == task_id:
            if payload.title is not None:
                task["title"] = payload.title
            if payload.done is not None:
                task["done"] = payload.done
            return task
    raise HTTPException(status_code=404, detail=f"Task {task_id} not found")


@app.delete("/tasks/{task_id}", status_code=204)
def delete_task(task_id: int):
    for idx, task in enumerate(tasks):
        if task["id"] == task_id:
            tasks.pop(idx)
            return None
    raise HTTPException(status_code=404, detail=f"Task {task_id} not found")
