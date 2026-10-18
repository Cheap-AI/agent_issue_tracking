"""DB-backed tests for backend/core/chat.py. Opt-in only - see tests/conftest.py.

Tests clean up their own rows (delete_session) since there's no global reset.
"""
import unittest

from backend.core.chat import append_message, get_or_create_session, list_messages
from backend.core.db import get_session
from backend.models.db_models import ChatSession


def _delete_session(session_id: str) -> None:
    with get_session() as db:
        row = db.get(ChatSession, session_id)
        if row is not None:
            db.delete(row)


class ChatCoreTests(unittest.TestCase):
    def setUp(self) -> None:
        self.session_id = "test-chat-session-core"
        self.addCleanup(_delete_session, self.session_id)

    def test_get_or_create_session_is_idempotent(self) -> None:
        first = get_or_create_session(self.session_id)
        second = get_or_create_session(self.session_id)
        self.assertEqual(first["id"], self.session_id)
        self.assertEqual(first["id"], second["id"])

    def test_append_and_list_messages_in_order(self) -> None:
        get_or_create_session(self.session_id)
        append_message(self.session_id, "user", "hello")
        append_message(self.session_id, "assistant", "hi there")

        messages = list_messages(self.session_id)
        self.assertEqual(len(messages), 2)
        self.assertEqual([m["role"] for m in messages], ["user", "assistant"])
        self.assertEqual(messages[0]["content"], "hello")
        self.assertEqual(messages[1]["content"], "hi there")

    def test_append_message_rejects_unknown_role(self) -> None:
        get_or_create_session(self.session_id)
        with self.assertRaises(ValueError):
            append_message(self.session_id, "system", "nope")
