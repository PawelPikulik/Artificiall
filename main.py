from fastapi import FastAPI, HTTPException, Request, Query, Depends
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field
from typing import Optional

import db
import auth

app = FastAPI(
    title="Task API",
    version="2.0.0",
    description="A secure CRUD API for managing tasks with Supabase authentication.",
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
        return response.user
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@app.post("/auth/login", summary="Log In")
def login(payload: LoginRequest):
    """Authenticate user and return JWT tokens."""
    try:
        response = auth.sign_in(payload.email, payload.password)
        if response.session is None:
            raise HTTPException(status_code=401, detail="Invalid login credentials")
        return {
            "access_token": response.session.access_token,
            "refresh_token": response.session.refresh_token,
            "user": response.user,
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
