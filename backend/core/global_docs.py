"""Shared global knowledge documents (rubric/ranking/taxonomy) backed by Postgres.

Replaces the previous file-based storage (storage/global/*.md).
"""
from datetime import datetime, timezone
from typing import Any

from backend.core.db import get_session
from backend.models.db_models import GlobalDoc

KNOWN_DOCS = ("rubric", "ranking", "taxonomy")


def get_doc(name: str) -> str | None:
    """Return the content of a global doc, or None if it doesn't exist."""
    with get_session() as session:
        doc = session.get(GlobalDoc, name)
        return doc.content if doc else None


def update_doc(name: str, content: str) -> dict[str, Any]:
    """Create or overwrite a global doc's content. Returns the doc as a dict."""
    with get_session() as session:
        doc = session.get(GlobalDoc, name)
        if doc is None:
            doc = GlobalDoc(name=name, content=content)
            session.add(doc)
        else:
            doc.content = content
            doc.updated_at = datetime.now(timezone.utc)
        session.flush()
        session.refresh(doc)
        return {"name": doc.name, "content": doc.content, "updated_at": doc.updated_at.isoformat()}
