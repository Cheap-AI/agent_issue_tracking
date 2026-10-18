"""Chat agent: streaming tool-calling assistant over existing read-only knowledge
plus a single action tool (trigger_discovery) that kicks off a background discovery run.

Unlike the discovery agent's non-streaming loop, intermediate tool-calling rounds are
accumulated silently and only the final natural-language answer is streamed token-by-token.
"""
from __future__ import annotations

import json
import logging
import os
from pathlib import Path
from typing import Any, Generator

from langfuse.openai import OpenAI
from langfuse import get_client

from backend.core.chat import append_message, get_or_create_session, list_messages
from backend.core.global_docs import get_doc
from backend.core.issue import get_issue, list_issues
from backend.core.job_registry import get_job, start_job
from backend.core.knowledge import read_current, read_history
from backend.agents.ranking.agent import get_leaderboard
from backend.services.vector_search import (
    search_similar_content,
    search_similar_issues_by_text,
    search_similar_reports,
    search_within_issue,
)
from backend.workflows.discover_issue import discover_issue
from backend.workflows.monthly_reports import get_latest_monthly_report, list_monthly_report_versions

logger = logging.getLogger(__name__)

client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
langfuse = get_client()

PROMPT_PATH = Path(__file__).resolve().parents[2] / "prompts" / "chat" / "system_prompt.md"
DEFAULT_MODEL = os.getenv("OPENAI_CHAT_MODEL", "gpt-4o")
MAX_TOOL_ROUNDS = 4


def _load_system_prompt() -> str:
    if PROMPT_PATH.exists():
        return PROMPT_PATH.read_text(encoding="utf-8")
    return (
        "You are a helpful assistant over this issue-tracking platform's knowledge base. "
        "Use the available tools to answer questions, and keep answers concise."
    )


TOOLS = [
    {
        "type": "function",
        "function": {
            "name": "list_issues",
            "description": "List tracked issues, optionally filtered by target year/month.",
            "parameters": {
                "type": "object",
                "properties": {
                    "target_year": {"type": "integer"},
                    "target_month": {"type": "integer", "minimum": 1, "maximum": 12},
                },
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_issue",
            "description": "Get full details for a single issue by id.",
            "parameters": {
                "type": "object",
                "properties": {"issue_id": {"type": "string"}},
                "required": ["issue_id"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "search_similar_issues_by_text",
            "description": "Semantic search over issues by free text, returns the closest matching issues.",
            "parameters": {
                "type": "object",
                "properties": {
                    "candidate_text": {"type": "string"},
                    "top_k": {"type": "integer", "minimum": 1, "maximum": 20},
                },
                "required": ["candidate_text"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "search_similar_content",
            "description": "Semantic search over issue knowledge components (research/summary/timeline/sources/questions).",
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {"type": "string"},
                    "top_k": {"type": "integer", "minimum": 1, "maximum": 20},
                    "component_types": {"type": "array", "items": {"type": "string"}},
                },
                "required": ["query"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "search_within_issue",
            "description": "Semantic search restricted to a single issue's knowledge components.",
            "parameters": {
                "type": "object",
                "properties": {
                    "issue_id": {"type": "string"},
                    "query": {"type": "string"},
                    "top_k": {"type": "integer", "minimum": 1, "maximum": 20},
                },
                "required": ["issue_id", "query"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "search_similar_reports",
            "description": "Semantic search over past per-run discovery reports.",
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {"type": "string"},
                    "top_k": {"type": "integer", "minimum": 1, "maximum": 20},
                },
                "required": ["query"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_leaderboard",
            "description": "Get the current top-ranked issues leaderboard.",
            "parameters": {
                "type": "object",
                "properties": {"limit": {"type": "integer", "minimum": 1, "maximum": 100}},
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_latest_monthly_report",
            "description": "Get the latest versioned monthly discovery report for a given year/month.",
            "parameters": {
                "type": "object",
                "properties": {
                    "year": {"type": "integer"},
                    "month": {"type": "integer", "minimum": 1, "maximum": 12},
                },
                "required": ["year", "month"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "list_monthly_report_versions",
            "description": "List all versions of the monthly discovery report for a given year/month.",
            "parameters": {
                "type": "object",
                "properties": {
                    "year": {"type": "integer"},
                    "month": {"type": "integer", "minimum": 1, "maximum": 12},
                },
                "required": ["year", "month"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "read_current",
            "description": "Read the current (latest) version of a knowledge component for an issue.",
            "parameters": {
                "type": "object",
                "properties": {
                    "issue_id": {"type": "string"},
                    "component": {
                        "type": "string",
                        "enum": ["research", "summary", "timeline", "sources", "questions"],
                    },
                },
                "required": ["issue_id", "component"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "read_history",
            "description": "List all version numbers of a knowledge component for an issue.",
            "parameters": {
                "type": "object",
                "properties": {
                    "issue_id": {"type": "string"},
                    "component": {
                        "type": "string",
                        "enum": ["research", "summary", "timeline", "sources", "questions"],
                    },
                },
                "required": ["issue_id", "component"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_doc",
            "description": "Read a shared global doc (rubric, ranking, or taxonomy).",
            "parameters": {
                "type": "object",
                "properties": {"name": {"type": "string", "enum": ["rubric", "ranking", "taxonomy"]}},
                "required": ["name"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "trigger_discovery",
            "description": (
                "Start a new discovery run in the background to find and create issues on a topic. "
                "Returns immediately with a job_id; this can take minutes to finish. "
                "Only call this when the user clearly asks to find/create new issues."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "topic": {"type": "string"},
                    "instruction": {"type": "string"},
                    "target_issue_count": {"type": "integer", "minimum": 1, "maximum": 20},
                },
                "required": ["topic", "instruction"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "check_discovery_status",
            "description": "Check the status/result of a previously triggered discovery job.",
            "parameters": {
                "type": "object",
                "properties": {"job_id": {"type": "string"}},
                "required": ["job_id"],
            },
        },
    },
]


def _tool_trigger_discovery(topic: str, instruction: str, target_issue_count: int = 1) -> dict[str, Any]:
    job_id = start_job(
        discover_issue,
        topic=topic,
        instruction=instruction,
        target_issue_count=target_issue_count,
    )
    return {"job_id": job_id, "status": "queued"}


def _tool_check_discovery_status(job_id: str) -> dict[str, Any]:
    job = get_job(job_id)
    if job is None:
        return {"status": "unknown", "message": f"No job found with id {job_id}"}
    return job


def _dispatch_tool(name: str, arguments: dict[str, Any]) -> dict[str, Any]:
    if name == "list_issues":
        return {"issues": list_issues(target_year=arguments.get("target_year"), target_month=arguments.get("target_month"))}
    if name == "get_issue":
        return {"issue": get_issue(arguments["issue_id"])}
    if name == "search_similar_issues_by_text":
        return {"results": search_similar_issues_by_text(arguments["candidate_text"], top_k=int(arguments.get("top_k", 5)))}
    if name == "search_similar_content":
        return {
            "results": search_similar_content(
                arguments["query"],
                top_k=int(arguments.get("top_k", 5)),
                component_types=arguments.get("component_types"),
            )
        }
    if name == "search_within_issue":
        return {
            "results": search_within_issue(
                arguments["issue_id"], arguments["query"], top_k=int(arguments.get("top_k", 3))
            )
        }
    if name == "search_similar_reports":
        return {"results": search_similar_reports(arguments["query"], top_k=int(arguments.get("top_k", 5)))}
    if name == "get_leaderboard":
        return {"leaderboard": get_leaderboard(limit=int(arguments.get("limit", 50)))}
    if name == "get_latest_monthly_report":
        return {"report": get_latest_monthly_report(arguments["year"], arguments["month"])}
    if name == "list_monthly_report_versions":
        return {"versions": list_monthly_report_versions(arguments["year"], arguments["month"])}
    if name == "read_current":
        result = read_current(arguments["issue_id"], arguments["component"])
        if result is None:
            return {"version": None, "content": None}
        version, content = result
        return {"version": version, "content": content}
    if name == "read_history":
        return {"versions": read_history(arguments["issue_id"], arguments["component"])}
    if name == "get_doc":
        return {"content": get_doc(arguments["name"])}
    if name == "trigger_discovery":
        return _tool_trigger_discovery(
            arguments["topic"], arguments["instruction"], int(arguments.get("target_issue_count", 1))
        )
    if name == "check_discovery_status":
        return _tool_check_discovery_status(arguments["job_id"])
    raise ValueError(f"Unknown tool: {name}")


def _history_to_messages(session_id: str) -> list[dict[str, Any]]:
    messages: list[dict[str, Any]] = [{"role": "system", "content": _load_system_prompt()}]
    for message in list_messages(session_id):
        if message["role"] in ("user", "assistant"):
            messages.append({"role": message["role"], "content": message["content"]})
    return messages


def stream_chat_response(session_id: str, user_message: str) -> Generator[dict[str, Any], None, None]:
    """Yield streaming events for a chat turn: {"type": "token"|"tool_call"|"done", ...}.

    Persists the user message immediately and the final assistant answer once the stream ends.
    """
    get_or_create_session(session_id)
    append_message(session_id, "user", user_message)
    messages = _history_to_messages(session_id)  # includes the user message just persisted above

    agent_span = langfuse.start_observation(
        as_type="agent", name="chat_turn", input={"session_id": session_id, "user_message": user_message}
    )
    final_text = ""
    try:
        for _round in range(MAX_TOOL_ROUNDS):
            stream = client.chat.completions.create(
                model=DEFAULT_MODEL,
                messages=messages,
                tools=TOOLS,
                tool_choice="auto",
                temperature=0.3,
                stream=True,
            )

            content_buffer = ""
            tool_call_buffer: dict[int, dict[str, Any]] = {}
            is_tool_round = False

            for chunk in stream:
                delta = chunk.choices[0].delta
                if delta.tool_calls:
                    is_tool_round = True
                    for tool_call_delta in delta.tool_calls:
                        entry = tool_call_buffer.setdefault(
                            tool_call_delta.index, {"id": "", "name": "", "arguments": ""}
                        )
                        if tool_call_delta.id:
                            entry["id"] = tool_call_delta.id
                        if tool_call_delta.function and tool_call_delta.function.name:
                            entry["name"] = tool_call_delta.function.name
                        if tool_call_delta.function and tool_call_delta.function.arguments:
                            entry["arguments"] += tool_call_delta.function.arguments
                elif delta.content:
                    content_buffer += delta.content
                    if not is_tool_round:
                        yield {"type": "token", "text": delta.content}

            if not is_tool_round:
                final_text = content_buffer
                break

            messages.append(
                {
                    "role": "assistant",
                    "content": content_buffer,
                    "tool_calls": [
                        {
                            "id": entry["id"],
                            "type": "function",
                            "function": {"name": entry["name"], "arguments": entry["arguments"]},
                        }
                        for entry in tool_call_buffer.values()
                    ],
                }
            )
            for entry in tool_call_buffer.values():
                tool_arguments = json.loads(entry["arguments"] or "{}")
                yield {"type": "tool_call", "name": entry["name"]}
                with agent_span.start_as_current_observation(
                    as_type="tool", name=entry["name"], input=tool_arguments
                ) as tool_span:
                    try:
                        tool_result = _dispatch_tool(entry["name"], tool_arguments)
                        tool_span.update(output=tool_result)
                    except Exception as exc:
                        tool_span.update(level="ERROR", status_message=str(exc))
                        tool_result = {"error": str(exc)}
                messages.append(
                    {"role": "tool", "tool_call_id": entry["id"], "content": json.dumps(tool_result)}
                )
        else:
            final_text = final_text or "I wasn't able to finish that within the allowed number of steps."
    except Exception as exc:
        agent_span.update(level="ERROR", status_message=str(exc))
        raise
    finally:
        agent_span.update(output={"final_text": final_text})

    append_message(session_id, "assistant", final_text)
    yield {"type": "done"}
