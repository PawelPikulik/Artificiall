# AI Prompt — Stage 7 Rematch

Build a simple to-do task API in Python using FastAPI. Here is what I need:

**Storage:** In-memory only (a list of dictionaries). No database, no files. The data should reset on server restart.

**Pre-seeded data:** Start with 3 example tasks: id 1 "Buy groceries" (not done), id 2 "Walk the dog" (done), id 3 "Read a book" (not done).

**Endpoints and status codes:**
- GET / — return JSON with name "Task API", version "1.0", and a list of endpoints
- GET /health — return { "status": "ok" }
- GET /tasks — return all tasks as a JSON array (status 200)
- GET /tasks/{id} — return one task by id (status 200). If the id doesn't exist, return status 404 with JSON { "error": "Task X not found" }
- POST /tasks — create a new task. The request body is JSON with a "title" field. Auto-assign the next free id, set done to false, and return the created task with status 201. If the title is missing or empty, return status 400 with a JSON error message.
- PUT /tasks/{id} — update a task's title and/or done status from the request body. Return the updated task (status 200). Unknown id → 404. Invalid body → 400.
- DELETE /tasks/{id} — remove the task and return status 204 with empty body. Unknown id → 404.

**Validation:** POST and PUT must validate that the title is present and not empty. Return 400 with a clear JSON error if validation fails.

**Swagger UI:** FastAPI should generate this automatically at /docs. Add a one-line description to each endpoint so the docs look good.

**Extras (optional but nice):** Add GET /stats that returns total, done, and open counts. Add query parameters to GET /tasks for filtering by done=true/false and searching by title text.

Keep the whole file under 120 lines. Run on localhost:8000.
