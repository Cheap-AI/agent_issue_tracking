from fastapi import APIRouter, Depends, HTTPException

import json

from fastapi.responses import StreamingResponse

from backend.agents.chat.agent import stream_chat_response
from backend.core.auth import CurrentUser, get_current_user
from backend.core.rate_limit import rate_limit
from backend.core.chat import claim_session, list_messages as list_chat_messages
from backend.models.schemas import ChatMessageRequest

router = APIRouter()


def _claim_or_403(session_id: str, user: CurrentUser) -> dict[str, object]:
    try:
        return claim_session(session_id, user.id)
    except PermissionError:
        raise HTTPException(status_code=403, detail="Not your chat session")


@router.post("/api/chat/sessions/{session_id}")
def create_chat_session(session_id: str, user: CurrentUser = Depends(get_current_user)) -> dict[str, object]:
    """Create (or return) the chat session with this client-generated id, owned by the caller."""
    return {"session": _claim_or_403(session_id, user)}


@router.get("/api/chat/sessions/{session_id}/messages")
def get_chat_messages(session_id: str, user: CurrentUser = Depends(get_current_user)) -> dict[str, object]:
    """List message history for one of the caller's chat sessions, for the widget to hydrate on load."""
    _claim_or_403(session_id, user)
    return {"messages": list_chat_messages(session_id)}


@router.post(
    "/api/chat/sessions/{session_id}/messages",
    dependencies=[Depends(rate_limit("chat_burst", 10, 60)), Depends(rate_limit("chat_daily", 200, 86400))],
)
def post_chat_message(
    session_id: str, payload: ChatMessageRequest, user: CurrentUser = Depends(get_current_user)
) -> StreamingResponse:
    """Stream the assistant's reply as newline-delimited JSON events."""
    _claim_or_403(session_id, user)

    def _event_stream():
        for event in stream_chat_response(session_id, payload.message):
            yield json.dumps(event) + "\n"

    return StreamingResponse(_event_stream(), media_type="application/x-ndjson")
