# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Commands

### Development

Run both frontend and backend together:
```
npm run dev
```

Run separately:
```
npm run dev:frontend        # Next.js on http://localhost:3000
npm run dev:backend         # FastAPI on http://127.0.0.1:8000
```

Backend only (no npm):
```
python -m uvicorn backend.main:app --host 127.0.0.1 --port 8000 --reload
```

### Setup

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r backend/requirements.txt
npm install
```

### Database migrations

```
alembic upgrade head        # apply all migrations
alembic revision -m "name"  # create a new migration
```

### Tests

```
pytest                      # run all tests
pytest tests/test_api.py    # run a single file
pytest -k "test_name"       # run a single test
```

## Architecture

**Monorepo** with a Next.js frontend (`frontend/`) and a FastAPI backend (`backend/`). Deployed to Vercel (frontend) and Render (backend). Database is Supabase Postgres with pgvector.

### Backend (`backend/`)

- **`main.py`** — FastAPI app setup only (CORS, lifespan, health routes, router registration). Long-running work is dispatched via `BackgroundTasks`.
- **`routers/`** — API routes grouped by area: `issues`, `discovery` (incl. leaderboard), `reports`, `chat`, `agentic`.
- **`telemetry.py`** — Langfuse client + OpenTelemetry FastAPI instrumentation (set up before other imports in `main.py`).
- **`core/`** — Database access layer: `issue.py` (CRUD), `chat.py`, `knowledge.py` (issue components + background embeddings), `db.py` (SQLAlchemy session/engine), `llm.py` (shared OpenAI client + `load_prompt`), `versioning.py`, `job_registry.py`.
- **`models/`** — `db_models.py` (SQLAlchemy ORM), `schemas.py` (Pydantic request bodies).
- **`workflows/`** — Multi-step orchestration:
  - `discover_issue.py` — autonomous topic discovery loop using Tavily/Perplexity; writes issues to DB.
  - `update_issue.py` — `quick_update` runs research → summary → ranking in sequence.
  - `langgraph_agentic_pipeline.py` — LangGraph `StateGraph` with human-in-the-loop via `interrupt()`. Stages: discover_research → judge → summarize_rank → judge → human review → persist. Uses in-memory checkpointing (runs lost on restart).
  - `collect_events.py`, `discovery_reports.py`, `monthly_reports.py` — supporting workflows.
- **`agents/`** — Individual LLM agents (each has an `agent.py`):
  - `chat/` — streaming chat agent (NDJSON over SSE).
  - `discovery/` — autonomous issue discovery.
  - `discover_research/` — combined discovery + research for the agentic pipeline.
  - `judge/` — evaluates research and summary quality; outputs approve/retry.
  - `ranking/` — scores issues, updates leaderboard (`leaderboard.json`), manages `tracked_issues`.
  - `researcher/` — deep research on a single issue.
  - `summarize_rank/` — generates executive summary then ranks.
- **`services/`** — `embedding.py` (OpenAI `text-embedding-3-small`), `vector_search.py` (pgvector), `search_service.py` (Tavily), `perplexity_service.py`, `chunking.py`.
- **`prompts/`** — Markdown system prompts for discovery and chat agents.
- **`storage/global/`** — Shared markdown files for ranking rubric and taxonomy, read at runtime.
- **`migrations/`** — Alembic migration scripts. Current schema includes: issues, events, tracked_issues (with tags, why, target_date), embeddings, RAG tables, monthly reports, chat tables.

### Frontend (`frontend/`)

Next.js 16 / React 19 / TypeScript / Tailwind CSS app. The `frontend/app/` directory holds page routes. It calls the backend over HTTP; in production it targets the Render URL, locally it hits `http://127.0.0.1:8000`.

### Environment variables

Copy `.env.example` to `.env`. Required keys: `DATABASE_URL`, `OPENAI_API_KEY`, `TAVILY_API_KEY`. Optional: `PERPLEXITY_API_KEY`, `LANGFUSE_*` (for observability via self-hosted Langfuse), `OPENAI_DISCOVERY_MODEL`.

### Observability

Langfuse is used throughout via `propagate_attributes` / `start_as_current_observation`. All agent and workflow calls are traced. For local use, run Langfuse via Docker (see `DEPLOYMENT.md`).
