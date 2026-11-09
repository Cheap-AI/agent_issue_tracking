"""Issue CRUD backed by Postgres (Supabase).

Replaces the previous file-based storage (meta.json per issue folder).
"""
from datetime import datetime, timezone
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from backend.core.db import get_session
from backend.core.tags import (
    SPACES,
    canonicalize,
    split_legacy_tags,
    union_tags,
    vocabulary_from_rows,
)
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
        "geography": issue.geography or [],
        "topics": issue.topics or [],
        "affected_groups": issue.affected_groups or [],
        "origin_year": issue.origin_year,
        "origin_precision": issue.origin_precision,
        "origin_confidence": issue.origin_confidence,
        "origin_basis": issue.origin_basis,
        "is_active": issue.is_active,
        "target_year": issue.target_year,
        "target_month": issue.target_month,
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
    target_year: int | None = None,
    target_month: int | None = None,
    session: Session | None = None,
    geography: list[str] | None = None,
    topics: list[str] | None = None,
    affected_groups: list[str] | None = None,
) -> dict[str, Any]:
    """Create a new issue row. Returns the issue as a dict.

    Tags go into three spaces. Legacy flat ``tags`` are sorted into spaces for callers that
    have not moved over yet. Values are matched to existing spellings (case-insensitive).
    """
    def _create(db: Session) -> dict[str, Any]:
        requested = {
            "geography": list(geography or []),
            "topics": list(topics or []),
            "affected_groups": list(affected_groups or []),
        }
        for space, values in split_legacy_tags(tags).items():
            requested[space].extend(values)
        existing = get_tag_vocabulary(db)
        clean = {
            space: canonicalize(requested[space], [v["value"] for v in existing[space]])
            for space in SPACES
        }

        next_number = db.execute(select(issue_id_seq.next_value())).scalar_one()
        new_id = f"iss-{next_number:04d}"

        issue = Issue(
            id=new_id,
            title=title.strip(),
            summary=summary.strip(),
            why=why.strip(),
            tags=union_tags(clean["geography"], clean["topics"], clean["affected_groups"]),
            geography=clean["geography"],
            topics=clean["topics"],
            affected_groups=clean["affected_groups"],
            is_active=True,
            target_year=target_year,
            target_month=target_month,
        )
        db.add(issue)
        db.flush()
        db.refresh(issue)
        return _issue_to_dict(issue)

    return _run_with_session(session, _create)


def set_issue_origin(
    issue_id: str,
    origin_year: int | None,
    origin_precision: str | None,
    origin_confidence: str | None,
    origin_basis: str | None,
    session: Session | None = None,
) -> dict[str, Any] | None:
    """Store an (already validated) origin estimate. Returns the issue dict, or None if not found."""
    def _set(db: Session) -> dict[str, Any] | None:
        issue = db.get(Issue, issue_id)
        if issue is None:
            return None
        issue.origin_year = origin_year
        issue.origin_precision = origin_precision
        issue.origin_confidence = origin_confidence
        issue.origin_basis = origin_basis
        db.flush()
        return _issue_to_dict(issue)

    return _run_with_session(session, _set)


def get_tag_vocabulary(session: Session | None = None) -> dict[str, list[dict[str, Any]]]:
    """Values already in use per tag space, most used first: {space: [{value, count}]}."""
    def _vocab(db: Session) -> dict[str, list[dict[str, Any]]]:
        rows = db.execute(select(Issue.geography, Issue.topics, Issue.affected_groups)).all()
        return vocabulary_from_rows(
            {"geography": g, "topics": t, "affected_groups": a} for g, t, a in rows
        )

    return _run_with_session(session, _vocab)


def list_issues(
    session: Session | None = None,
    target_year: int | None = None,
    target_month: int | None = None,
) -> list[dict[str, Any]]:
    """List issues, ordered by id. Optionally filter by target_year and/or target_month."""
    def _list(db: Session) -> list[dict[str, Any]]:
        query = select(Issue)
        if target_year is not None:
            query = query.where(Issue.target_year == target_year)
        if target_month is not None:
            query = query.where(Issue.target_month == target_month)
        issues = db.execute(query.order_by(Issue.id)).scalars().all()
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

