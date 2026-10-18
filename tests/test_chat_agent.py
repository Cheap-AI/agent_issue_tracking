"""Mocked tests for backend/agents/chat/agent.py - no real OpenAI network calls or DB writes."""
import unittest
from types import SimpleNamespace
from unittest.mock import patch

from backend.agents.chat import agent


def _delta(content=None, tool_calls=None):
    return SimpleNamespace(content=content, tool_calls=tool_calls)


def _chunk(delta):
    return SimpleNamespace(choices=[SimpleNamespace(delta=delta)])


def _tool_call_delta(index, call_id=None, name=None, arguments=None):
    function = SimpleNamespace(name=name, arguments=arguments)
    return SimpleNamespace(index=index, id=call_id, function=function)


class ChatAgentStreamingTests(unittest.TestCase):
    def setUp(self) -> None:
        patch.object(agent, "get_or_create_session", lambda session_id: {"id": session_id}).start()
        patch.object(agent, "append_message", lambda *a, **k: None).start()
        patch.object(agent, "list_messages", lambda session_id: []).start()
        self.addCleanup(patch.stopall)

    def test_final_answer_streams_token_by_token(self) -> None:
        chunks = [
            _chunk(_delta(content="Hel")),
            _chunk(_delta(content="lo!")),
        ]
        with patch.object(agent, "client") as mock_client:
            mock_client.chat.completions.create.return_value = iter(chunks)
            events = list(agent.stream_chat_response("session-1", "hi"))

        token_events = [e for e in events if e["type"] == "token"]
        self.assertEqual("".join(e["text"] for e in token_events), "Hello!")
        self.assertEqual(events[-1]["type"], "done")

    def test_tool_call_round_executes_tool_then_streams_final_answer(self) -> None:
        tool_round = [
            _chunk(_delta(tool_calls=[_tool_call_delta(0, call_id="call_1", name="get_leaderboard", arguments="")])),
            _chunk(_delta(tool_calls=[_tool_call_delta(0, arguments="{}")])),
        ]
        final_round = [_chunk(_delta(content="Top issue is X."))]

        with patch.object(agent, "client") as mock_client, patch.object(
            agent, "get_leaderboard", return_value=[{"issue_id": "iss-0001"}]
        ) as mock_leaderboard:
            mock_client.chat.completions.create.side_effect = [iter(tool_round), iter(final_round)]
            events = list(agent.stream_chat_response("session-2", "what's the top issue?"))

        mock_leaderboard.assert_called_once()
        tool_call_events = [e for e in events if e["type"] == "tool_call"]
        self.assertEqual(tool_call_events, [{"type": "tool_call", "name": "get_leaderboard"}])
        token_events = [e for e in events if e["type"] == "token"]
        self.assertEqual("".join(e["text"] for e in token_events), "Top issue is X.")

    def test_dispatch_unknown_tool_raises(self) -> None:
        with self.assertRaises(ValueError):
            agent._dispatch_tool("not_a_real_tool", {})
