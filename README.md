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
