"""Chat session/message CRUD backed by Postgres.

Sessions are per-browser: the id is a UUID string generated client-side.
"""
from datetime import datetime, timezone
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from backend.core.db import get_session
from backend.models.db_models import ChatMessage, ChatSession

ROLES = ("user", "assistant", "tool")


def _utcnow_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _session_to_dict(session_row: ChatSession) -> dict[str, Any]:
    return {
        "id": session_row.id,
        "title": session_row.title,
        "created_at": session_row.created_at.isoformat() if session_row.created_at else _utcnow_iso(),
    }


def _message_to_dict(message: ChatMessage) -> dict[str, Any]:
    return {
        "id": message.id,
        "session_id": message.session_id,
        "role": message.role,
        "content": message.content,
        "tool_calls": message.tool_calls,
        "created_at": message.created_at.isoformat() if message.created_at else _utcnow_iso(),
    }


def _run_with_session(provided_session: Session | None, operation):
    if provided_session is not None:
        return operation(provided_session)
    with get_session() as managed_session:
        return operation(managed_session)


def get_or_create_session(
    session_id: str, title: str | None = None, session: Session | None = None
) -> dict[str, Any]:
    """Return the chat session with this id, creating it if it doesn't exist yet."""
    def _get_or_create(db: Session) -> dict[str, Any]:
        existing = db.get(ChatSession, session_id)
        if existing is not None:
            return _session_to_dict(existing)
        row = ChatSession(id=session_id, title=title)
        db.add(row)
        db.flush()
        db.refresh(row)
        return _session_to_dict(row)

    return _run_with_session(session, _get_or_create)


def list_messages(session_id: str, session: Session | None = None) -> list[dict[str, Any]]:
    """List messages for a session in chronological order."""
    def _list(db: Session) -> list[dict[str, Any]]:
        messages = db.execute(
            select(ChatMessage)
            .where(ChatMessage.session_id == session_id)
            .order_by(ChatMessage.created_at, ChatMessage.id)
        ).scalars().all()
        return [_message_to_dict(message) for message in messages]

    return _run_with_session(session, _list)


def append_message(
    session_id: str,
    role: str,
    content: str,
    tool_calls: list | None = None,
    session: Session | None = None,
) -> dict[str, Any]:
    """Append a message to a session. Raises ValueError for an unknown role."""
    if role not in ROLES:
        raise ValueError(f"Unknown chat message role: {role!r}")

    def _append(db: Session) -> dict[str, Any]:
        message = ChatMessage(
            session_id=session_id,
            role=role,
            content=content,
            tool_calls=tool_calls,
        )
        db.add(message)
        db.flush()
        db.refresh(message)
        return _message_to_dict(message)

    return _run_with_session(session, _append)
