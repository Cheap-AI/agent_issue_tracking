# Testing Checklist - Discovery RAG & Deduplication System

**Date:** 2026-08-11  
**Status:** Ready for testing after Alembic migration 0007 and data wipe

---

## ✅ Pre-Testing Setup (Completed)

- [x] Run `alembic upgrade head` (applied migration 0007)
- [x] Delete all issues data: `DELETE FROM issues;`
- [x] Verify new tables exist: `issue_embeddings`, `discovery_reports`, `discovery_report_chunks`
- [x] Backend running: `python -m uvicorn backend.main:app --host 127.0.0.1 --port 8000 --reload`

---

## 1. Database Schema Validation

### Tables Created (Migration 0007)
- [ ] `issue_embeddings` table exists with columns:
  - `id` (BIGSERIAL PK)
  - `issue_id` (VARCHAR UNIQUE FK → issues.id CASCADE)
  - `embedding` (vector(1536))
  - `created_at` (TIMESTAMPTZ)
- [ ] `discovery_reports` table exists with columns:
  - `id` (BIGSERIAL PK)
  - `topic`, `instruction`, `target_count`, `actual_created`, `iterations`, `review_mode`
  - `api_usage`, `findings`, `proposed_duplicates`, `summary` (JSONB)
  - `created_at` (TIMESTAMPTZ)
- [ ] `discovery_report_chunks` table exists with columns:
  - `id` (BIGSERIAL PK)
  - `report_id` (FK → discovery_reports.id CASCADE)
  - `chunk_index`, `chunk_text`, `embedding` (vector(1536))
  - `created_at` (TIMESTAMPTZ)

### Indexes Created
- [ ] `issue_embeddings_embedding_idx` (ivfflat cosine similarity)
- [ ] `discovery_reports_created_at_idx` (time-based queries)
- [ ] `discovery_report_chunks_embedding_idx` (ivfflat cosine similarity)
- [ ] `discovery_report_chunks_report_id_idx` (join optimization)

**Verification:**
```sql
SELECT table_name FROM information_schema.tables WHERE table_schema = 'public' AND table_name IN ('issue_embeddings', 'discovery_reports', 'discovery_report_chunks');
```

---

## 2. Discovery Agent - Semantic Deduplication

### New Tools Available
- [ ] `check_similar_issues(candidate_text, top_k=5)` callable by agent
- [ ] `merge_into_issue(issue_id, additional_info, reason)` callable by agent
- [ ] `create_issue` accepts optional `dimension_scores` parameter

### Deduplication Workflow
- [ ] Agent calls `check_similar_issues` before creating new issues
- [ ] When similarity >= 0.9:
  - [ ] Agent uses `merge_into_issue` instead of `create_issue`
  - [ ] Merge appends additional_info to existing issue
  - [ ] Re-embeds merged issue with updated content
  - [ ] Merge tracked in `proposed_duplicates` list
- [ ] When similarity 0.75-0.9:
  - [ ] Agent skips creation (gray zone)
  - [ ] Candidate flagged in agent reasoning
  - [ ] Tracked in `proposed_duplicates` list
- [ ] When similarity < 0.75:
  - [ ] Agent proceeds with `create_issue`
  - [ ] Embedding stored automatically via `store_issue_embedding()`

### System Prompt Updates
- [ ] Dedup workflow instructions present in [discovery system_prompt.md](backend/prompts/discovery/system_prompt.md)
- [ ] Examples of merge vs. skip vs. create scenarios documented
- [ ] Tool usage code examples included

**Test Command:**
```bash
python -m backend.workflows.discover_issue "technology trends 2026"
```

**Expected Behavior:**
- First run: creates issues with embeddings
- Second run: detects duplicates, merges high-similarity candidates

---

## 3. Discovery Reports - Postgres Storage

### Report Generation
- [ ] `generate_report()` builds structured report from discovery run
- [ ] Captures API usage: Tavily calls, Perplexity calls, queries
- [ ] Captures findings: created issues with id, title, summary, why, tags
- [ ] Captures proposed_duplicates: candidates that were merged or skipped (0.75-0.9 similarity)
- [ ] Captures summary: total_created, success_rate, final_message

### Report Storage
- [ ] `save_report()` inserts to `discovery_reports` table (returns report_id)
- [ ] Builds digest text from report metadata, queries, findings, duplicates
- [ ] `chunk_text()` splits digest into semantic chunks
- [ ] `generate_embeddings_batch()` embeds all chunks
- [ ] Inserts chunks to `discovery_report_chunks` with embeddings

### Report Retrieval
- [ ] `load_recent_reports(limit=10)` queries Postgres (newest first)
- [ ] Returns list of report dicts with all metadata
- [ ] `get_discovery_insights()` aggregates stats from all reports:
  - [ ] total_reports, total_issues_created
  - [ ] api_calls (tavily, perplexity, total)
  - [ ] average_issues_per_run
  - [ ] most_effective_queries (top 5)
  - [ ] most_common_tags (top 10)
  - [ ] api_preference (% Tavily vs Perplexity)

**Test Command:**
```python
from backend.workflows.discovery_reports import load_recent_reports, get_discovery_insights
reports = load_recent_reports(limit=5)
insights = get_discovery_insights()
print(insights)
```

**Verification:**
```sql
SELECT COUNT(*) FROM discovery_reports;
SELECT COUNT(*) FROM discovery_report_chunks;
SELECT topic, actual_created, created_at FROM discovery_reports ORDER BY created_at DESC LIMIT 5;
```

---

## 4. RAG-Based Semantic Memory

### Daily Cap Check
- [ ] `_runs_today()` queries `discovery_reports.created_at` (not JSON files)
- [ ] Counts runs in current UTC day
- [ ] Enforces `max_daily_attempts` cap (default 10)

### Memory Context Building
- [ ] `_build_memory_context(topic, instruction)` uses semantic search
- [ ] Calls `search_similar_reports(query, top_k=3)` with topic+instruction
- [ ] Returns relevant chunks from past discovery runs
- [ ] Also loads last 5 recent reports for broader context
- [ ] No JSON file I/O (removed `storage/discovery_runs.json`, `storage/discovery_agent_memory.json`)

### Semantic Search
- [ ] `search_similar_reports()` in vector_search.py:
  - [ ] Generates embedding for query
  - [ ] Searches `discovery_report_chunks` with cosine similarity
  - [ ] Joins to `discovery_reports` for metadata
  - [ ] Returns top_k chunks with report context
- [ ] `search_similar_issues_by_text()` for deduplication:
  - [ ] Generates embedding for candidate text
  - [ ] Searches `issue_embeddings` with cosine similarity
  - [ ] Returns issue_id, title, similarity (0-1)

**Test Command:**
```python
from backend.services.vector_search import search_similar_reports
results = search_similar_reports("AI safety and ethics", top_k=3)
print(results)
```

---

## 5. Discovery Workflow Integration

### Workflow: discover_issue.py
- [ ] Checks daily cap from Postgres (not JSON)
- [ ] Builds memory context from semantic search (not JSON)
- [ ] Calls `discover_issues()` with memory_context
- [ ] Generates report with `generate_report()`
- [ ] Saves report to Postgres with `save_report()` (returns report_id, not file path)
- [ ] Returns result with:
  - [ ] `created_issues` list
  - [ ] `proposed_duplicates` list
  - [ ] `report.report_id` (integer, not JSON path)
  - [ ] `report.proposed_duplicates_count`
  - [ ] `runs_today` count

### Workflow: update_issue.py (Writer Removed)
- [ ] `update_issue_workflow()` runs research → ranking only
- [ ] NO summary step (writer agent removed)
- [ ] `quick_update()` runs research → ranking
- [ ] No import of `backend.agents.writer.agent`

**Test Command:**
```bash
# Full discovery run
python -m backend.workflows.discover_issue "climate change impacts"

# Quick update (research + ranking)
python -c "from backend.workflows.update_issue import quick_update; print(quick_update('iss-0001', 'climate change'))"
```

---

## 6. API Endpoints

### GET /api/discovery/reports?limit=10
- [ ] Returns recent reports from Postgres
- [ ] Each report includes: timestamp, metadata, api_usage, findings, proposed_duplicates, summary
- [ ] Response format:
  ```json
  {
    "reports": [...],
    "count": 5,
    "status": "success"
  }
  ```

### GET /api/discovery/insights
- [ ] Returns aggregated insights from all reports
- [ ] Includes: total_reports, total_issues_created, api_calls, average_issues_per_run, most_effective_queries, most_common_tags, api_preference

### POST /api/discovery
- [ ] Accepts: topic, instruction, target_issue_count, etc.
- [ ] Calls `discover_issue()` workflow
- [ ] Returns result with created_issues, proposed_duplicates, report metadata

**Test Commands:**
```bash
curl http://127.0.0.1:8000/api/discovery/reports?limit=5
curl http://127.0.0.1:8000/api/discovery/insights
curl -X POST http://127.0.0.1:8000/api/discovery -H "Content-Type: application/json" -d '{"topic": "healthcare", "target_issue_count": 5}'
```

---

## 7. End-to-End Integration Tests

### Test 1: First Discovery Run (Clean Slate)
```bash
python -m backend.workflows.discover_issue "AI technology trends"
```
- [ ] Creates 3-5 new issues
- [ ] Stores embeddings for each issue in `issue_embeddings`
- [ ] Saves report to `discovery_reports`
- [ ] Saves report chunks to `discovery_report_chunks`
- [ ] No duplicates detected (first run)

### Test 2: Second Discovery Run (Dedup Triggered)
```bash
python -m backend.workflows.discover_issue "artificial intelligence developments"
```
- [ ] Detects similar existing issues (>= 0.9 similarity)
- [ ] Merges into existing issues instead of creating duplicates
- [ ] Tracks merges in `proposed_duplicates` list
- [ ] Updates embeddings for merged issues
- [ ] Report includes proposed_duplicates count

### Test 3: RAG Memory Recall
```bash
python -m backend.workflows.discover_issue "machine learning ethics"
```
- [ ] Memory context includes chunks from past "AI" runs (semantic similarity)
- [ ] Agent sees past queries and strategies
- [ ] Agent avoids repeating ineffective searches

### Test 4: Daily Cap Enforcement
Run discovery 11 times in one day:
```bash
for i in {1..11}; do python -m backend.workflows.discover_issue "test $i"; done
```
- [ ] First 10 runs succeed
- [ ] 11th run raises: `RuntimeError: Discovery daily cap reached (10 runs today)`

### Test 5: API Report Retrieval
```bash
curl http://127.0.0.1:8000/api/discovery/reports?limit=3
curl http://127.0.0.1:8000/api/discovery/insights
```
- [ ] Reports endpoint returns last 3 reports from Postgres
- [ ] Insights endpoint returns aggregated stats
- [ ] No JSON file references (all data from Postgres)

---

## 8. Deployment Readiness

### Environment Variables (Render)
- [ ] `DATABASE_URL` (Supabase connection string)
- [ ] `OPENAI_API_KEY` (for embeddings and agent reasoning)
- [ ] `TAVILY_API_KEY` (for web search)
- [ ] `PERPLEXITY_API_KEY` (for research-focused search)
- [ ] All set with `sync: false` in [render.yaml](render.yaml)

### Build Command
- [ ] `pip install -r backend/requirements.txt && alembic upgrade head`
- [ ] Migrations run automatically on deploy

### Verification Post-Deploy
```bash
# Check tables exist
curl https://your-app.onrender.com/api/issues
curl https://your-app.onrender.com/api/discovery/insights

# Run discovery
curl -X POST https://your-app.onrender.com/api/discovery -H "Content-Type: application/json" -d '{"topic": "test", "target_issue_count": 2}'
```

---

## 9. Known Issues & Follow-Up Tasks

### Not Yet Implemented
- [ ] `merge_into_issue()` TODO: Actually update issue.summary in database (currently just re-embeds)
- [ ] `create_issue()` with `dimension_scores` TODO: Store scores in tracked_issues table
- [ ] API authentication (deferred - public endpoints for now)

### Future Enhancements
- [ ] Frontend UI for viewing discovery reports
- [ ] Discovery report detail page with API usage charts
- [ ] Manual duplicate resolution UI
- [ ] Tag taxonomy validation/autocomplete

---

## Testing Order

1. **Schema validation** (verify tables/indexes exist)
2. **Unit tests** (individual functions: vector search, report storage)
3. **Discovery agent** (single run, verify dedup tools work)
4. **Discovery workflow** (end-to-end with Postgres storage)
5. **RAG memory** (multiple runs, verify semantic recall)
6. **API endpoints** (verify reports/insights return Postgres data)
7. **Daily cap** (verify limit enforcement)
8. **Deployment** (Render with env vars)

---

## Success Criteria

✅ System is production-ready when:
- All tables created with proper indexes
- Discovery runs create issues with embeddings
- Deduplication merges high-similarity candidates (>= 0.9)
- Reports saved to Postgres with chunked embeddings
- Memory context uses semantic search (no JSON files)
- API endpoints return Postgres data
- Daily cap enforced from Postgres
- Render deployment successful with all env vars

🎉 **Ready to test!**
