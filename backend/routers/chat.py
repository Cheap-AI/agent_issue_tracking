from fastapi import APIRouter

import json

from fastapi.responses import StreamingResponse

from backend.agents.chat.agent import stream_chat_response
from backend.core.chat import get_or_create_session, list_messages as list_chat_messages
from backend.models.schemas import ChatMessageRequest

router = APIRouter()


@router.post("/api/chat/sessions/{session_id}")
def create_chat_session(session_id: str) -> dict[str, object]:
    """Create (or return) the chat session with this client-generated id."""
    return {"session": get_or_create_session(session_id)}


@router.get("/api/chat/sessions/{session_id}/messages")
def get_chat_messages(session_id: str) -> dict[str, object]:
    """List message history for a chat session, for the widget to hydrate on load."""
    return {"messages": list_chat_messages(session_id)}


@router.post("/api/chat/sessions/{session_id}/messages")
def post_chat_message(session_id: str, payload: ChatMessageRequest) -> StreamingResponse:
    """Stream the assistant's reply as newline-delimited JSON events."""
    def _event_stream():
        for event in stream_chat_response(session_id, payload.message):
            yield json.dumps(event) + "\n"

    return StreamingResponse(_event_stream(), media_type="application/x-ndjson")
