"""Versioned knowledge component storage backed by Postgres (Supabase).

Replaces the previous file-based storage (v001.md, v002.md, ... per component folder).
Concurrency-safe: uses a Postgres advisory lock scoped to (issue_id, component) so
concurrent writers can't race on the next version number.
"""
from sqlalchemy import func, select, text

from backend.core.db import get_session
from backend.models.db_models import Component


def _advisory_lock_key(issue_id: str, component: str) -> str:
    return f"{issue_id}:{component}"


def save_version(issue_id: str, component: str, content: str) -> int:
    """Write `content` as the next immutable version of a component. Returns the new version number."""
    with get_session() as session:
        session.execute(
            text("SELECT pg_advisory_xact_lock(hashtext(:key))"),
            {"key": _advisory_lock_key(issue_id, component)},
        )
        current_max = session.execute(
            select(func.max(Component.version)).where(
                Component.issue_id == issue_id, Component.component_type == component
            )
        ).scalar_one_or_none()
        next_version = (current_max or 0) + 1

        session.add(
            Component(
                issue_id=issue_id,
                component_type=component,
                version=next_version,
                content=content,
            )
        )
        return next_version


def get_current_version(issue_id: str, component: str) -> tuple[int, str] | None:
    """Return (version_number, content) for the latest version of a component, or None if none exist."""
    with get_session() as session:
        row = session.execute(
            select(Component.version, Component.content)
            .where(Component.issue_id == issue_id, Component.component_type == component)
            .order_by(Component.version.desc())
            .limit(1)
        ).first()
        if row is None:
            return None
        return row.version, row.content


def list_versions(issue_id: str, component: str) -> list[int]:
    """Return all existing version numbers for a component, ascending."""
    with get_session() as session:
        versions = session.execute(
            select(Component.version)
            .where(Component.issue_id == issue_id, Component.component_type == component)
            .order_by(Component.version.asc())
        ).scalars().all()
        return list(versions)

