# Plan: Research persistence with SQLAlchemy + Tavily seed

## Decisions (confirmed with user)
- Research results go in a separate `research_results`/`research_queries` table, NOT merged into `issues`.
- Introduce SQLAlchemy (migrate off raw sqlite3) for the new tables (and existing issues table for consistency).
- Also run one real Tavily seed call now using the query "give me 10 most important issues for the last 7 days" (max_results=10) to populate sample data end-to-end.

## Discovery notes
- Live backend is `api/` (api/index.py, api/database.py) — the `backend/` folder referenced in the stale workspace tree no longer exists (removed earlier).
- `api/database.py` currently uses raw sqlite3 with `ISSUE_DB_PATH` env var (default `issues.db`), functions: `get_connection`, `init_db`, `list_issues`, `create_issue`.
- `api/index.py` has `/api/health`, GET/POST `/api/issues`, POST `/api/agent/research` (now calls real Tavily client, added TAVILY_API_KEY + python-dotenv already).
- `tests/test_api.py` is STALE/BROKEN — references `api_module.issues_db` (in-memory list) which no longer exists since persistence moved to SQLite. Must fix as part of this work.
- `tests/test_database.py` is a good pattern to mirror for the new research tables (uses tempdir + env var override + importlib.reload).
- `api/requirements.txt` has tavily-python, python-dotenv, fastapi, uvicorn, pydantic, openai, langchain-community, requests. Needs `sqlalchemy` added.
- Tavily client already initialized in api/index.py as `tavily` (None if no key). User has now set a real key in `.env`.

## Steps

### Phase 1: Data model & persistence layer (SQLAlchemy)
1. Add `sqlalchemy>=2.0` to `api/requirements.txt`.
2. Create `api/models.py` with SQLAlchemy declarative models:
   - `Issue`: id, title, summary, created_at
   - `ResearchQuery`: id, query_text, status, created_at
   - `ResearchResult`: id, query_id (FK -> ResearchQuery.id), title, url, content, created_at
3. Refactor `api/database.py` to use a SQLAlchemy engine/session (same SQLite file, path still driven by `ISSUE_DB_PATH`), but KEEP the existing function signatures (`init_db()`, `list_issues()`, `create_issue(title, summary)`) so `api/index.py` and existing tests need minimal changes. Add new helpers: `create_research_query(query_text)`, `add_research_result(query_id, title, url, content)`, `list_research_queries()`, `get_research_results(query_id)`.
4. `init_db()` creates all tables via `Base.metadata.create_all`.

### Phase 2: Wire endpoints (*depends on Phase 1*)
5. In `api/index.py`, extract a shared `perform_research(topic: str, max_results: int = 5) -> dict` helper used by both the endpoint and the seed script — calls Tavily, persists a `ResearchQuery` row + `ResearchResult` rows, returns the same shape the frontend expects (topic/status/summary/sources).
6. Update `POST /api/agent/research` to call `perform_research(topic)` and persist.
7. Add `GET /api/research` returning stored research queries + their results (for future UI use).

### Phase 3: Seed script (*depends on Phase 2*)
8. Create `scripts/seed_research.py`: calls `perform_research("give me 10 most important issues for the last 7 days", max_results=10)` using the real backend DB (respects `ISSUE_DB_PATH`/default `issues.db`). Run manually once (not part of automated pytest suite, since it needs a real network call + API key).

### Phase 4: Tests & verification (*Phase 1-2 can be tested independently with a mocked Tavily client; Phase 3 is manual*)
9. Fix `tests/test_api.py` — remove `issues_db` references, align with SQLite-backed issues (mirror the tempdir/env-var override pattern from `tests/test_database.py`).
10. Add `tests/test_research_db.py` — persistence-layer tests for `create_research_query`/`add_research_result`/listing, following the same tempdir + reload pattern.
11. Add a test for `perform_research` / the `/api/agent/research` endpoint with the Tavily client mocked/monkeypatched (no real network call in automated tests).
12. Run `pytest` for the whole `tests/` folder — confirm all green.
13. Manually run `scripts/seed_research.py` once (with the real key already set in `.env`) and inspect rows (extend `inspect_issues.py` or query directly) to confirm real data landed.

## Relevant files
- `api/requirements.txt` — add sqlalchemy
- `api/models.py` (new) — Issue, ResearchQuery, ResearchResult declarative models
- `api/database.py` — refactor to SQLAlchemy session/engine, add research CRUD helpers, keep existing function signatures
- `api/index.py` — extract `perform_research()`, update research endpoint, add GET /api/research
- `scripts/seed_research.py` (new) — one-off manual seed using the real Tavily key
- `tests/test_api.py` — fix stale `issues_db` references
- `tests/test_research_db.py` (new) — persistence tests for research tables
- `tests/test_database.py` — reference pattern only, no changes needed unless issues table helpers change signature

## Scope boundaries
- NOT building a "promote research result to issue" feature now (future extension).
- NOT adding a frontend UI for viewing stored research yet (GET /api/research is API-only for now).
- NOT running the seed script automatically in CI/tests — it's a manual one-time run with the real API key.

---

# Plan: Agentic issue-curation (tracked_issues top-50 list)

Status: Phases 1-4 above are DONE (persistence + basic research endpoint). This is the next feature layer, built on top.

## Decisions confirmed with user
- **No MCP.** MCP standardizes tool exposure for *external* AI hosts (Claude Desktop, VS Code, etc.) we don't control. Since our own FastAPI backend is the LLM host and orchestrator, we use **native OpenAI/Anthropic tool/function calling** directly — a structured, schema-validated mechanism, not free-text query parsing.
- **Bounded iteration for v1**: use a real tool-calling loop (model can call `tavily_search` more than once, sees results, decides to refine or stop) but capped at a small max iteration count (e.g. 3-4 calls) so v1 stays deterministic/testable — this reconciles "start smaller" with "use the real native mechanism from day one" instead of one hardcoded query.
- **New table `tracked_issues`** — separate from `issues` (manual) and `research_results` (raw one-off search hits). This is a persistent, evolving leaderboard of ~50 curated issues.
- **Dimension scores stored as JSON** (not fixed columns) for extensibility — starting set: severity/impact + recency. User has NOT finalized the full dimension list yet (may add credibility, urgency, breadth of impact later) — JSON storage avoids a schema migration when that happens.
- **Dedup via LLM semantic judgment** — compare new candidate title/description against existing tracked_issues, not URL/string heuristics.
- **Trigger: on-demand script only** (like `seed_research.py`), no scheduling/cron for now.
- **Ranking/trimming**: keep top 50 by `composite_score` as `is_active=True`; when there are more than 50, deactivate (soft, reversible) the lowest-ranked rather than deleting rows.

## Steps

### Phase 5: Schema for tracked_issues
1. Add `TrackedIssue` model to `api/models.py`: `id`, `title`, `description`, `dimension_scores` (JSON/Text), `composite_score` (float), `source_urls` (JSON/Text), `first_seen_at`, `last_confirmed_at`, `is_active` (bool, default True), `created_at`.
2. Add CRUD helpers to `api/database.py`: `create_tracked_issue(...)`, `list_tracked_issues(active_only=True)`, `update_tracked_issue(id, ...)`, `deactivate_tracked_issue(id)`, `get_tracked_issue_by_id(id)`.

### Phase 6: Tool-calling agent loop (*depends on Phase 5*)
3. New module `api/agent.py` implementing:
   - A `tavily_search(query, max_results)` tool schema for OpenAI tool-calling.
   - A bounded loop (max ~3-4 iterations): system prompt describes the curation goal + current dimension rubric; model can call the search tool, see raw results appended as tool messages, then either call again with a refined query or stop.
   - Final step: ask the model for **structured output** (JSON) — a list of candidate issues, each with title, description, dimension scores, and source urls. Use JSON mode / a strict schema so parsing is reliable (not regex-scraping free text).

### Phase 7: Dedup + ranking + persistence (*depends on Phase 6*)
4. For each candidate issue, one LLM call comparing it against existing `tracked_issues` (title/description) to decide: new vs. duplicate-of-existing-id.
5. Merge logic: duplicates → update `last_confirmed_at` (and blend/replace score); new candidates → insert.
6. Recompute `composite_score` for all active tracked issues, sort descending, keep top 50 `is_active=True`, deactivate the rest.

### Phase 8: Trigger script + tests (*depends on Phase 7*)
7. `scripts/curate_issues.py` (new) — on-demand entrypoint running the full pipeline (search loop → extract → dedup → rank → persist).
8. `tests/test_tracked_issues.py` (new) — with OpenAI + Tavily clients mocked (no real network/LLM calls in CI):
   - persistence/ranking helpers (create, list active, trim to top 50, deactivate)
   - bounded loop respects max iteration cap
   - dedup logic merges a duplicate candidate instead of inserting a new row
9. Run `pytest tests/` — confirm green.
10. Manual run of `scripts/curate_issues.py` once with real keys, inspect via an extended `inspect_research.py` (or new `inspect_tracked_issues.py`) to confirm real curated data landed.

## Relevant files
- `api/models.py` — add `TrackedIssue`
- `api/database.py` — add tracked_issues CRUD + ranking/trim helpers
- `api/agent.py` (new) — tool-calling loop, candidate extraction, dedup logic
- `scripts/curate_issues.py` (new) — on-demand trigger
- `tests/test_tracked_issues.py` (new) — persistence + ranking + mocked agent-loop tests
- `api/requirements.txt` — `openai` already present (supports tool calling); no MCP dependency needed

## Scope boundaries
- No MCP server/client — direct tool calling only, since we are our own LLM host.
- No scheduling/cron — on-demand script trigger only for now.
- Dimension rubric starts minimal (severity/impact, recency) but stored as extensible JSON — full rubric still TBD by user.
- Iteration is bounded (small max call count), not an unlimited/open-ended search loop, to keep v1 deterministic and testable.
