# Task API

A simple CRUD API for managing tasks, built with FastAPI and **PostgreSQL** running in Docker.

## Why PostgreSQL + Docker?

PostgreSQL is a production-grade relational database. Docker lets us run it locally with zero system installation, and `docker compose up` starts the entire stack (database + app) in one command. A named volume persists PostgreSQL data across container restarts, so tasks survive even when the container is recreated.

## Quick start

1. **Clone the repository**
   ```bash
   git clone https://github.com/PawelPikulik/Artificiall.git
   cd Artificiall
   ```

2. **Create the environment file**
   ```bash
   cp .env.example .env
   ```
   The `.env` file is already gitignored. `.env.example` is committed as a template.

3. **Start the stack**
   ```bash
   docker compose up
   ```
   This starts PostgreSQL and the FastAPI app. The first run creates the database and seeds the `tasks` table automatically via `init.sql`.

4. **Open in browser**
   - API root: http://localhost:8000/
   - Swagger UI (interactive docs): http://localhost:8000/docs

## Architecture

The API layer (`main.py`) is completely unchanged from Week 2 and Week 3. The only difference is the storage implementation (`db.py`), which now uses **psycopg2** to talk to PostgreSQL instead of **sqlite3**.

```
Client -> API (main.py) -> PostgreSQL repository (db.py) -> PostgreSQL in Docker
```

This proves that swapping storage is an implementation detail — the routes, request bodies, and responses remain identical.

## Database

- **Engine**: PostgreSQL 15 (Alpine image)
- **Table**: `tasks` with columns `id` (SERIAL PRIMARY KEY), `title` (TEXT), `done` (BOOLEAN)
- **Seed data**: Three example tasks are inserted automatically on first container startup via `init.sql`
- **Persistence**: Data survives both app restarts and container restarts thanks to the `postgres_data` Docker volume

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

## Example SQL query

Connect to the running PostgreSQL container and run queries directly:

```bash
docker exec -it artificiall-db psql -U artificiall -d artificiall -c "SELECT * FROM tasks WHERE done = TRUE;"
```

## Example curl session

```bash
# Start the stack first: docker compose up

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

## The persistence experiment

Create a few tasks, then run `docker compose down` followed by `docker compose up`. The tasks are still there because the PostgreSQL data is stored in a named Docker volume (`postgres_data`) that persists across container restarts.

This is the core difference from Week 2 (in-memory) and a step up from Week 3 (SQLite file): the database itself is now a separate service with its own persistent storage.

## Extras included

- **Filtering & search**: `GET /tasks?done=true` returns only finished tasks; `GET /tasks?search=milk` returns tasks whose title contains the word. Both are implemented with SQL `WHERE` clauses in PostgreSQL.
- **Stats endpoint**: `GET /stats` returns `{ "total": 7, "done": 3, "open": 4 }` using SQL `COUNT()`.
- **Reset endpoint**: `POST /reset` restores the 3 example tasks, handy for demos.

## Testing

A test suite (`test_api.py`) covers all endpoints. Run it while the stack is up:

```bash
python test_api.py
```

## Database viewer screenshot

![DB Browser for SQLite showing the tasks table](screenshot.png)

> *Screenshot taken from Week 3 (SQLite). The same table now lives in PostgreSQL inside Docker.*
