"""Issue CRUD backed by Postgres (Supabase).

Replaces the previous file-based storage (meta.json per issue folder).
"""
from datetime import datetime, timezone
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from backend.core.db import get_session
from backend.models.db_models import Event, Issue, issue_id_seq

COMPONENTS = ("research", "summary", "timeline", "sources", "questions")


def _utcnow_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _issue_to_dict(issue: Issue) -> dict[str, Any]:
    return {
        "id": issue.id,
        "title": issue.title,
        "summary": issue.summary,
        "why": issue.why,
        "tags": issue.tags or [],
        "is_active": issue.is_active,
        "created_at": issue.created_at.isoformat() if issue.created_at else _utcnow_iso(),
    }


def _run_with_session(
    provided_session: Session | None,
    operation,
):
    if provided_session is not None:
        return operation(provided_session)
    with get_session() as managed_session:
        return operation(managed_session)


def create_issue(
    title: str,
    summary: str,
    why: str = "",
    tags: list[str] | None = None,
    session: Session | None = None,
) -> dict[str, Any]:
    """Create a new issue row. Returns the issue as a dict."""
    def _create(db: Session) -> dict[str, Any]:
        next_number = db.execute(select(issue_id_seq.next_value())).scalar_one()
        new_id = f"iss-{next_number:04d}"

        issue = Issue(
            id=new_id,
            title=title.strip(),
            summary=summary.strip(),
            why=why.strip(),
            tags=tags or [],
            is_active=True,
        )
        db.add(issue)
        db.flush()
        db.refresh(issue)
        return _issue_to_dict(issue)

    return _run_with_session(session, _create)


def list_issues(session: Session | None = None) -> list[dict[str, Any]]:
    """List all issues, ordered by id."""
    def _list(db: Session) -> list[dict[str, Any]]:
        issues = db.execute(select(Issue).order_by(Issue.id)).scalars().all()
        return [_issue_to_dict(issue) for issue in issues]

    return _run_with_session(session, _list)


def get_issue(issue_id: str, session: Session | None = None) -> dict[str, Any] | None:
    """Return a single issue as a dict, or None if it doesn't exist."""
    def _get(db: Session) -> dict[str, Any] | None:
        issue = db.get(Issue, issue_id)
        if issue is None:
            return None
        return _issue_to_dict(issue)

    return _run_with_session(session, _get)


def delete_issue(issue_id: str, session: Session | None = None) -> bool:
    """Delete an issue by id. Returns True if deleted, False if not found."""
    def _delete(db: Session) -> bool:
        issue = db.get(Issue, issue_id)
        if issue is None:
            return False
        db.delete(issue)
        db.commit()
        return True

    return _run_with_session(session, _delete)


def _event_to_dict(event: Event) -> dict[str, Any]:
    return {
        "id": event.id,
        "event_date": event.event_date.isoformat() if event.event_date else None,
        "discovered_at": event.discovered_at.isoformat() if event.discovered_at else _utcnow_iso(),
        "title": event.title,
        "description": event.description,
        "source_urls": event.source_urls or [],
    }


def list_events_for_issue(issue_id: str, session: Session | None = None) -> list[dict[str, Any]]:
    """List events for an issue in chronological order.

    Ordered by event_date ascending (nulls last), then discovered_at ascending
    as a tiebreaker/fallback for events without a known date.
    """
    def _list(db: Session) -> list[dict[str, Any]]:
        events = db.execute(
            select(Event)
            .where(Event.issue_id == issue_id)
            .order_by(Event.event_date.is_(None), Event.event_date.asc(), Event.discovered_at.asc())
        ).scalars().all()
        return [_event_to_dict(event) for event in events]

    return _run_with_session(session, _list)

