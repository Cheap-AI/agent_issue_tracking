# Data Model and Storage Architecture

This document describes the current data model and storage structure following the removal of SQLite/SQLAlchemy in favor of a fully file-based system.

## 1. Storage Overview

All application data is stored under the `storage/` directory.

```
storage/
  global/                 - Shared framework documents
  issues/                 - Folder per tracked issue
    iss-0001/             - Unique Issue ID
      meta.json           - Issue metadata (title, summary, status)
      research/           - Versioned research markdown files
      summary/            - Versioned summary markdown files
      timeline/           - Versioned timeline events
      sources/            - Versioned source lists
      questions/          - Versioned open questions
```

## 2. Issue Metadata (`meta.json`)

Stored at `storage/issues/<id>/meta.json`.

| Field | Type | Description |
| :--- | :--- | :--- |
| `id` | `string` | Sequential ID, e.g., `"iss-0001"`. |
| `title` | `string` | The macro issue title. |
| `summary` | `string` | The latest high-level executive summary. |
| `is_active` | `boolean` | Whether the issue is currently being tracked/ranked. |
| `created_at` | `iso8601` | Timestamp of initial discovery. |

## 3. Versioned Components

Each component folder (e.g., `research/`, `summary/`) contains immutable, sequential markdown files:
- `v001.md`, `v002.md`, `v003.md`...
- The **"current"** state of a component is always the file with the highest version number.
- History is preserved indefinitely.

## 4. Global Knowledge

Shared across the platform to define how agents think and rank.
- `storage/global/ranking.md`: Scoring formulas and weighting.
- `storage/global/rubric.md`: Evaluation dimensions (severity, impact, recency, etc.).
- `storage/global/taxonomy.md`: Categorization labels.

## 5. API Schemas (Pydantic)

Located in `backend/models/schemas.py`. These define the request/response shapes for the FastAPI endpoints but are not persisted as database tables.

- `IssueCreateRequest`: `{ title: str, summary: str }`
- `AgentRequest`: `{ topic: str }`
