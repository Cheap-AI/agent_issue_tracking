# Data Model and Storage Architecture

This document describes the current data model following the migration from file-based storage to Supabase Postgres.

## 1. Storage Overview

All application data lives in a Supabase Postgres database, accessed via SQLAlchemy from `backend/core/`.

```
issues            - One row per tracked issue (id, title, summary, is_active, created_at)
components        - Versioned knowledge rows (issue_id, component_type, version, content, created_at)
                    component_type in: research, summary, timeline, sources, questions
global_docs       - Shared framework documents (name, content, updated_at)
                    name in: rubric, ranking, taxonomy
```

## 2. Issue Metadata (`issues` table)

| Column | Type | Description |
| :--- | :--- | :--- |
| `id` | `text` (PK) | Sequential ID, e.g., `"iss-0001"`, generated from the `issue_id_seq` Postgres sequence. |
| `title` | `text` | The macro issue title. |
| `summary` | `text` | The latest high-level executive summary. |
| `is_active` | `boolean` | Whether the issue is currently being tracked/ranked. |
| `created_at` | `timestamptz` | Timestamp of initial discovery. |

## 3. Versioned Components (`components` table)

Each row is an immutable version of a knowledge component (`research`, `summary`, `timeline`, `sources`, `questions`):
- Unique on `(issue_id, component_type, version)`.
- The **"current"** state of a component is always the row with the highest `version` for that `(issue_id, component_type)`.
- History is preserved indefinitely (no updates/deletes, only inserts).
- Next version numbers are computed under a Postgres advisory lock (`pg_advisory_xact_lock`) to avoid race conditions between concurrent writers.

## 4. Global Knowledge (`global_docs` table)

Shared across the platform to define how agents think and rank. One row per name, upserted in place (not versioned):
- `rubric`: Evaluation dimensions (severity, impact, recency, etc.).
- `ranking`: Scoring formulas and weighting.
- `taxonomy`: Categorization labels.

## 5. API Schemas (Pydantic)

Located in `backend/models/schemas.py`. These define the request/response shapes for the FastAPI endpoints but are not persisted as database tables.

- `IssueCreateRequest`: `{ title: str, summary: str }`
- `AgentRequest`: `{ topic: str }`

