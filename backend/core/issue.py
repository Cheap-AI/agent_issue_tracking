"""Issue CRUD backed by Postgres (Supabase).

Replaces the previous file-based storage (meta.json per issue folder).
"""
from datetime import datetime, timezone
from typing import Any

from sqlalchemy import select

from backend.core.db import get_session
from backend.models.db_models import Issue, issue_id_seq

COMPONENTS = ("research", "summary", "timeline", "sources", "questions")


def _utcnow_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _issue_to_dict(issue: Issue) -> dict[str, Any]:
    return {
        "id": issue.id,
        "title": issue.title,
        "summary": issue.summary,
        "is_active": issue.is_active,
        "created_at": issue.created_at.isoformat() if issue.created_at else _utcnow_iso(),
    }


def create_issue(title: str, summary: str) -> dict[str, Any]:
    """Create a new issue row. Returns the issue as a dict."""
    with get_session() as session:
        next_number = session.execute(select(issue_id_seq.next_value())).scalar_one()
        new_id = f"iss-{next_number:04d}"

        issue = Issue(id=new_id, title=title.strip(), summary=summary.strip(), is_active=True)
        session.add(issue)
        session.flush()
        session.refresh(issue)
        return _issue_to_dict(issue)


def list_issues() -> list[dict[str, Any]]:
    """List all issues, ordered by id."""
    with get_session() as session:
        issues = session.execute(select(Issue).order_by(Issue.id)).scalars().all()
        return [_issue_to_dict(issue) for issue in issues]


def get_issue(issue_id: str) -> dict[str, Any] | None:
    """Return a single issue as a dict, or None if it doesn't exist."""
    with get_session() as session:
        issue = session.get(Issue, issue_id)
        if issue is None:
            return None
        return _issue_to_dict(issue)

