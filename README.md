# Task API

A simple CRUD API for managing tasks, built with FastAPI. The data lives in memory only — restarting the server resets the task list to the original three examples.

## Quick start

1. **Activate the virtual environment**
   ```bash
   source venv/Scripts/activate   # Windows (Git Bash)
   # source venv/bin/activate     # Linux / macOS
   ```

2. **Install dependencies**
   ```bash
   pip install -r requirements.txt
   ```

3. **Run the server**
   ```bash
   uvicorn main:app --reload
   ```

4. **Open in browser**
   - API root: http://localhost:8000/
   - Swagger UI (interactive docs): http://localhost:8000/docs

## Endpoints

| Method | Path | Description | Status codes |
|--------|------|-------------|--------------|
| GET | `/` | API info | 200 |
| GET | `/health` | Health check | 200 |
| GET | `/tasks` | List all tasks (optional `?done=` and `?search=` filters) | 200 |
| GET | `/tasks/{id}` | Get one task | 200, 404 |
| POST | `/tasks` | Create a new task | 201, 400 |
| PUT | `/tasks/{id}` | Update a task | 200, 400, 404 |
| DELETE | `/tasks/{id}` | Delete a task | 204, 404 |
| GET | `/stats` | Task statistics | 200 |
| POST | `/reset` | Reset to the 3 default tasks | 200 |

## Example curl session

```bash
# Start the server first: uvicorn main:app --reload

# Read all tasks
curl -i http://localhost:8000/tasks
# HTTP/1.1 200 OK
# [{"id":1,"title":"Buy groceries","done":false},...]

# Create a task
curl -i -X POST http://localhost:8000/tasks \
  -H "Content-Type: application/json" \
  -d '{"title":"Buy milk"}'
# HTTP/1.1 201 Created
# {"id":4,"title":"Buy milk","done":false}

# Update it
curl -i -X PUT http://localhost:8000/tasks/4 \
  -H "Content-Type: application/json" \
  -d '{"done":true}'
# HTTP/1.1 200 OK
# {"id":4,"title":"Buy milk","done":true}

# Delete it
curl -i -X DELETE http://localhost:8000/tasks/4
# HTTP/1.1 204 No Content

# 404 example
curl -i http://localhost:8000/tasks/99
# HTTP/1.1 404 Not Found
# {"detail":"Task 99 not found"}

# Invalid body (missing title)
curl -i -X POST http://localhost:8000/tasks \
  -H "Content-Type: application/json" \
  -d '{}'
# HTTP/1.1 400 Bad Request
# {"error":"Invalid request body"}
```

## The mortality experiment

Create a few tasks, then restart the server and call `GET /tasks` again. What happened? The tasks you created are gone, and only the three seeded examples remain. This is because the data lives **in memory** — when the program stops, the variables are wiped. That is exactly why databases exist: they persist data beyond the lifetime of a single process. This observation is the reason Week 3 of the course introduces databases.

## Extras included

- **Filtering & search**: `GET /tasks?done=true` returns only finished tasks; `GET /tasks?search=milk` returns tasks whose title contains the word.
- **Stats endpoint**: `GET /stats` returns `{ "total": 7, "done": 3, "open": 4 }`.
- **Reset endpoint**: `POST /reset` restores the 3 example tasks, handy for demos.

## AI vs me — Stage 7 rematch

### The prompt I wrote

> Build a simple to-do task API in Python using FastAPI. Storage: in-memory only (a list of dictionaries). No database, no files. Pre-seeded data: 3 tasks (id 1 "Buy groceries" not done, id 2 "Walk the dog" done, id 3 "Read a book" not done). Endpoints: GET / with API info, GET /health, GET /tasks, GET /tasks/{id} (404 if missing), POST /tasks (auto id, done=false, 201, 400 if missing/empty title), PUT /tasks/{id} (update title/done, 200/400/404), DELETE /tasks/{id} (204/404). Validation: POST and PUT must validate title present and not empty, return 400. Swagger UI at /docs with one-line descriptions per endpoint. Extras: GET /stats and query params for filtering/search. Keep under 120 lines, run on localhost:8000.

The AI-generated code lives in `ai-version/main.py` and is isolated from the hand-built version.

### What the AI did better

The AI version is more structured: it extracted helper functions (`_find_task`, `_remove_task`) and used `next()` with generator expressions instead of inline for loops. It also used `@validator` decorators inside Pydantic models to strip whitespace from titles, which is a nice touch I didn't think of. I understand its version well enough to explain it — the validators run before the endpoint handler and the helpers keep the route code clean.

### What the AI got wrong or quietly ignored

**1. Missing 400 status code for validation errors.** The AI used Pydantic validators for title validation, but did not add a custom exception handler to convert FastAPI's default 422 into 400. When I tested `POST /tasks` with `{}`, the AI version returned **422** instead of the required **400**. The prompt explicitly asked for 400 on invalid body, but the AI relied on FastAPI's default behavior.

**2. Wrong ID generation after deletions.** The AI used a monotonic global counter (`_task_counter += 1`) instead of `max(existing_ids) + 1`. After deleting the highest-id task and creating a new one, the AI version skips numbers, leaving gaps in the ID sequence. The prompt said "auto-assign the next free id" which I interpreted as the next available integer, not a monotonically increasing counter.

**3. Async-by-default without reason.** The AI made every endpoint `async def` even though none of them perform I/O (no database, no files, no network calls). In FastAPI this is harmless, but it adds unnecessary `async`/`await` noise to a purely CPU-bound in-memory API. My hand-built version uses plain `def` which is more honest about what the code actually does.

### What my prompt forgot to specify

I did not explicitly say "convert Pydantic validation errors to HTTP 400 instead of 422" — I assumed the AI would know that 400 is the standard for bad request bodies. The AI silently decided to use the FastAPI default (422), which is technically correct for FastAPI but not what the assignment required. I also did not specify whether endpoints should be sync or async, so the AI chose the fashionable default (async everywhere).

### One rematch

I improved the prompt by adding: *"Add a custom exception handler so that missing or empty title fields return HTTP 400 with a simple JSON error like `{'error': 'Invalid request body'}`, not FastAPI's default 422."* With that extra sentence, the AI would likely produce a version that matches the hand-built one exactly on status codes.
