# Artificiall

A full-stack AI Engineering portfolio built across five Backend AI Engineering assignments (BE-05 through BE-09).

This repository contains a **FastAPI backend** with PostgreSQL, Supabase Auth, LLM integration, background jobs, PDF generation, and a **Next.js frontend** for AI-powered visual workflows.

**Repository**: https://github.com/PawelPikulik/Artificiall

---

## Assignments Overview

| Assignment | Code | Topic | Key Deliverable |
|---|---|---|---|
| The Polite Scraper | BE-05 | Data collection | `books.json` — 60 validated books from books.toscrape.com |
| Your First Background Job | BE-06 | Async processing | `POST /tasks/{id}/analyze` → 202 Accepted, background LLM analysis with retries & idempotency |
| AI Task Analysis | BE-07 | LLM integration | Groq-powered structured analysis with Pydantic validation |
| PDF Report Generator | BE-08 | Artifact generation | Async PDF reports (task_summary, book_catalog) with scheduled recurrence |
| AI Decision Flow | BE-09 | Visual workflow builder | Next.js + React Flow + Inngest canvas for YES/NO decision graphs |

---

## Tech Stack

### Backend (Artificiall root)
- **FastAPI** — Python async web framework
- **PostgreSQL** — Dockerized relational database
- **Supabase Auth** — JWT Bearer token authentication
- **Groq API** — Free-tier LLM (llama-3.1-8b-instant)
- **fpdf2** — Pure-Python PDF generation
- **APScheduler** — Cron-style recurring jobs

### Frontend (ai-decision-flow/ subdirectory)
- **Next.js 16** — React framework with App Router
- **React Flow** — Visual node/edge canvas
- **Inngest** — Durable workflow execution
- **OpenAI SDK** — gpt-4o-mini for per-node decisions
- **shadcn/ui** — Component library

---

## Quick Start

### Prerequisites
- Docker Desktop (for PostgreSQL)
- Python 3.11+ (for local development without Docker)
- Node.js 18+ (for the AI Decision Flow frontend)
- A free [Supabase](https://supabase.com) project
- A free [Groq](https://console.groq.com/keys) API key

### 1. Environment Setup

```bash
git clone https://github.com/PawelPikulik/Artificiall.git
cd Artificiall
cp .env.example .env
```

Edit `.env`:
```
SUPABASE_URL=https://your-project.supabase.co
SUPABASE_KEY=your-anon-key
GROQ_API_KEY=gsk_your_key_here
```

### 2. Start the Backend

```bash
docker compose up --build
```

- API: http://localhost:8000
- Swagger UI: http://localhost:8000/docs

### 3. Run Tests

```bash
# Task CRUD tests
python test_api.py

# Background job tests (BE-06)
python test_jobs.py

# PDF report tests (BE-08)
python test_reports.py
```

### 4. Run the AI Decision Flow Frontend (optional)

```bash
cd ai-decision-flow
npm install
# Add OPENAI_API_KEY=sk-... to .env.local
npm run dev
```

- Frontend: http://localhost:3000

---

## Complete Endpoint Reference

### Public

| Method | Path | Auth | Description | Status |
|--------|------|------|-------------|--------|
| GET | `/` | No | API metadata | 200 |
| GET | `/health` | No | Health check | 200 |
| GET | `/public/info` | No | Public message | 200 |

### Authentication (Supabase)

| Method | Path | Auth | Description | Status |
|--------|------|------|-------------|--------|
| POST | `/auth/signup` | No | Create account | 201, 400 |
| POST | `/auth/login` | No | Log in, get JWT | 200, 401 |
| POST | `/auth/logout` | **Yes** | Invalidate session | 204, 401 |
| GET | `/protected/profile` | **Yes** | User profile | 200, 401 |

### Tasks

| Method | Path | Auth | Description | Status |
|--------|------|------|-------------|--------|
| GET | `/tasks` | No | List tasks (filter: `?done=true`, search: `?search=milk`) | 200 |
| GET | `/tasks/{id}` | No | Get single task | 200, 404 |
| POST | `/tasks` | No | Create task | 201, 400 |
| PUT | `/tasks/{id}` | No | Update task | 200, 400, 404 |
| DELETE | `/tasks/{id}` | No | Delete task | 204, 404 |
| GET | `/stats` | No | Task statistics (SQL COUNT) | 200 |
| POST | `/reset` | No | Restore default 3 tasks | 200 |

### AI Task Analysis (BE-06 + BE-07)

| Method | Path | Auth | Description | Status |
|--------|------|------|-------------|--------|
| POST | `/tasks/{id}/analyze` | **Yes** | Queue LLM analysis → 202 Accepted | 202, 401, 404 |
| GET | `/jobs/{id}` | **Yes** | Check job status & result | 200, 401, 404 |
| GET | `/tasks/{id}/analysis` | **Yes** | Shortcut to completed result | 200, 401, 404, 409 |

### PDF Reports (BE-08)

| Method | Path | Auth | Description | Status |
|--------|------|------|-------------|--------|
| POST | `/reports` | **Yes** | Queue PDF generation | 202, 401, 422 |
| GET | `/reports` | **Yes** | List your reports | 200, 401 |
| GET | `/reports/{id}` | **Yes** | Get report status | 200, 401, 404 |
| GET | `/reports/{id}/download` | **Yes** | Stream PDF file | 200, 401, 404, 409 |
| DELETE | `/reports/{id}` | **Yes** | Delete report + file | 204, 401, 404 |
| POST | `/reports/schedule` | **Yes** | Schedule recurring report (cron) | 201, 401, 422 |
| GET | `/reports/schedule` | **Yes** | List scheduled reports | 200, 401 |
| DELETE | `/reports/schedule/{id}` | **Yes** | Cancel scheduled report | 204, 401, 404 |

---

## Assignment Details

### BE-05: The Polite Scraper

Collects books from [books.toscrape.com](https://books.toscrape.com) with production-grade politeness:

- `urllib.robotparser` checks `robots.txt`
- Custom `User-Agent` with project name + GitHub link
- `time.sleep(1)` between page requests
- Broken pages caught and logged; scraper continues
- Every book validated through Pydantic `Book` schema
- Prices like `"£51.77"` cleaned to `51.77` before storage

```bash
python scraper.py
# Output: 60 books → books.json
```

**Files**: `scraper.py`, `schemas.py`, `books.json`

### BE-06: Your First Background Job

Moves the slow LLM call out of the HTTP request path.

**Pattern**: accept fast (202), work in background, report status.

**Non-negotiables implemented**:
- **Idempotency**: same task → same `job_id`, no duplicate LLM work
- **Retries**: 3 attempts with exponential backoff (1s → 2s → 4s)
- **Alerts**: full traceback stored in `jobs.error_message`, exposed via `GET /jobs/{id}`

```bash
# Queue analysis (returns in < 50ms)
curl -X POST http://localhost:8000/tasks/1/analyze \
  -H "Authorization: Bearer $TOKEN"
# → {"job_id": 1, "status": "pending", "status_url": "/jobs/1"}

# Poll for completion
curl http://localhost:8000/jobs/1 \
  -H "Authorization: Bearer $TOKEN"

# Shortcut: get result directly
curl http://localhost:8000/tasks/1/analysis \
  -H "Authorization: Bearer $TOKEN"
```

**Files**: `analysis_worker.py`, `test_jobs.py`, `jobs` table

### BE-07: AI Task Analysis

Sends task titles to Groq's free-tier LLM and returns structured, validated analysis.

**Trust features**:
- Pydantic schema validation (priority ∈ {High, Medium, Low}, estimated_minutes 0-10080)
- Configurable timeout (default 15s)
- Exponential backoff on 429/5xx (max 3 attempts)
- Graceful degradation: 503 on permanent LLM failure

```bash
curl -X POST http://localhost:8000/tasks/1/analyze \
  -H "Authorization: Bearer $TOKEN"
# → {"task_id": 1, "title": "Buy groceries",
#     "analysis": {"priority": "Medium", "category": "Errands",
#                  "estimated_minutes": 45, "reasoning": "..."}}
```

**Files**: `llm.py`

### BE-08: PDF Report Generator

Generates styled PDF reports from SQL-aggregated data and scraped JSON catalogs — asynchronously, with artifact storage and scheduled recurrence.

**Report types**:
| Type | Data source | Contents |
|------|-------------|----------|
| `task_summary` | PostgreSQL `tasks` | Counts, completion rate, full task list table |
| `book_catalog` | `books.json` (BE-05) | Price histogram, rating distribution, top 15 books |

**Artifact pattern**: PDF stored on disk in `reports/` directory; DB stores only the file path (never the binary).

```bash
# Queue report
curl -X POST http://localhost:8000/reports \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"report_type": "task_summary"}'

# Download
curl http://localhost:8000/reports/1/download \
  -H "Authorization: Bearer $TOKEN" \
  -o report.pdf

# Schedule weekly report (stretch)
curl -X POST http://localhost:8000/reports/schedule \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"report_type": "book_catalog", "cron": "0 9 * * 1"}'
```

**Files**: `report_generator.py`, `jobs.py`, `scheduler.py`, `test_reports.py`

### BE-09: AI Decision Flow

A visual workflow builder in `ai-decision-flow/` where each node is an AI decision step.

- **React Flow canvas** with custom YES/NO decision nodes
- **Per-node LLM execution** — sends prompt + input context to OpenAI gpt-4o-mini, gets strict YES/NO
- **Inngest workflow** — server-side graph traversal with `step.run`
- **Execution logs panel** — real-time logs, history, path tracing
- **Save / Load / Export / Import** — localStorage persistence + JSON
- **Visual state** — nodes and edges highlight during execution

```bash
cd ai-decision-flow
npm install
# Add OPENAI_API_KEY=sk-... to .env.local
npm run dev
```

**Files**: `ai-decision-flow/` subdirectory (Next.js 16 + React Flow + Inngest + shadcn/ui)

---

## Architecture

```
┌─────────────────────────────────────────────────────────────────────┐
│                          Artificiall Stack                          │
├─────────────────────────────────────────────────────────────────────┤
│  FastAPI (main.py)                                                  │
│  ├── Auth (Supabase JWT) ─────────────────────→ Supabase            │
│  ├── Tasks CRUD ────────────────────────────→ PostgreSQL          │
│  ├── AI Analysis (BE-06/07)                                         │
│  │   ├── POST /tasks/{id}/analyze → 202                           │
│  │   └── BackgroundTasks → analysis_worker.py → Groq LLM          │
│  ├── PDF Reports (BE-08)                                            │
│  │   ├── POST /reports → 202                                      │
│  │   └── BackgroundTasks → jobs.py → report_generator.py (fpdf2)  │
│  └── Scheduled Reports (stretch)                                    │
│       └── scheduler.py (APScheduler)                                │
├─────────────────────────────────────────────────────────────────────┤
│  ai-decision-flow/ (BE-09)                                          │
│  ├── Next.js 16 + React Flow canvas                                 │
│  ├── Inngest durable execution                                      │
│  └── OpenAI gpt-4o-mini per-node decisions                         │
└─────────────────────────────────────────────────────────────────────┘
```

---

## Environment Variables

| Variable | Required | Source |
|----------|----------|--------|
| `SUPABASE_URL` | Yes | Supabase Project Settings → API |
| `SUPABASE_KEY` | Yes | Supabase Project Settings → API |
| `SUPABASE_SERVICE_KEY` | No (dev) | Supabase → Service Role key (for auto-confirm) |
| `GROQ_API_KEY` | Yes | https://console.groq.com/keys |
| `DATABASE_URL` | Auto | `postgresql://artificiall:artificiall@db:5432/artificiall` (Docker) |

For the AI Decision Flow frontend:
| Variable | Required | Source |
|----------|----------|--------|
| `OPENAI_API_KEY` | Yes | https://platform.openai.com/api-keys |

---

## Testing

All test suites authenticate automatically, create test users, and clean up.

```bash
# Backend tests (run while docker compose up is running)
python test_api.py        # Task CRUD, auth, stats
python test_jobs.py       # Background jobs, idempotency, retries
python test_reports.py    # PDF generation, download, scheduled reports

# Frontend tests
cd ai-decision-flow
npm run build             # TypeScript compilation check
```

---

## Docker Services

```bash
docker compose up --build    # Start everything
docker compose down          # Stop everything
docker compose down -v       # Stop + wipe data volumes (destructive)
```

| Service | Port | Volume | Purpose |
|---------|------|--------|---------|
| PostgreSQL | 5432 | `postgres_data` | Task, job, report persistence |
| FastAPI app | 8000 | `reports_data` | PDF artifact storage |

---

## License

MIT

---

*Co-Authored-By: Warp <agent@warp.dev>*
