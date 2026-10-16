"""Discover & Research agent: finds a candidate issue AND researches it in one loop.

Merges what used to be two separate hops (discovery agent -> quick_update -> research agent)
into a single bounded tool-calling agent with one shared trace/context. Operates in DRAFT
MODE: it never writes to the database. `draft_create_issue` / `draft_merge_issue` just record
the agent's decision in the returned dict - actual persistence happens later, only after a
human approves the draft (see backend/workflows/langgraph_agentic_pipeline.py).
"""
from __future__ import annotations

import json
import logging
import os
from typing import Any

from langfuse.openai import OpenAI
from langfuse import get_client

from backend.core.issue import get_issue, list_issues
from backend.services import search_service
from backend.services import perplexity_service
from backend.services.vector_search import search_similar_issues_by_text

logger = logging.getLogger(__name__)

client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
langfuse = get_client()

DEFAULT_MODEL = os.getenv("OPENAI_DISCOVER_RESEARCH_MODEL", os.getenv("OPENAI_DISCOVERY_MODEL", "gpt-4o"))

SYSTEM_PROMPT = """You are a discover-and-research agent for an Issue Intelligence Platform.

Your job, in one pass:
1. Explore a topic (or explore autonomously if no topic is given) and find ONE specific,
   evidence-backed candidate issue worth tracking.
2. Check it isn't a near-duplicate of an existing issue.
3. Research it thoroughly: gather supporting evidence and any timestamped events
   (announcements, incidents, milestones) related to it.
4. Record your decision by calling exactly one of `draft_create_issue` or `draft_merge_issue`.

You do NOT write anything to the database yourself - these tools only draft a proposal that a
human will review later. Be thorough with research before drafting: a thin, generic dossier
will be rejected by a quality reviewer and sent back to you with feedback.

Call `collect_events` at least once to gather timestamped events before drafting, when relevant.
"""


# Tavily tool wrapper, mirrors discovery agent's tool.
def _tool_search_tavily(query: str, max_results: int = 10) -> dict[str, Any]:
    return {"query": query, "results": search_service.search(query, max_results=max_results)}


# Perplexity tool wrapper, mirrors discovery agent's tool (currently disabled upstream).
def _tool_search_perplexity(query: str) -> dict[str, Any]:
    if not perplexity_service.is_configured():
        return {"query": query, "results": [], "error": "Perplexity API not configured."}
    try:
        return {"query": query, "results": perplexity_service.search(query)}
    except Exception as e:
        logger.warning(f"Perplexity search failed for '{query}': {e}")
        return {"query": query, "results": [], "error": f"Perplexity search failed: {str(e)[:100]}"}


def _tool_list_issues() -> dict[str, Any]:
    return {"issues": list_issues()}


def _tool_get_issue(issue_id: str) -> dict[str, Any]:
    issue = get_issue(issue_id)
    return {"issue": issue}


def _tool_check_similar_issues(candidate_text: str, top_k: int = 5) -> dict[str, Any]:
    return {"similar_issues": search_similar_issues_by_text(candidate_text, top_k=top_k)}


# Searches for events and extracts them with GPT, WITHOUT persisting anything.
def _tool_collect_events(query: str, max_results: int = 10) -> dict[str, Any]:
    if not search_service.is_configured():
        return {"events": [], "error": "Tavily API not configured."}

    try:
        web_results = search_service.search(query, max_results=max_results)
    except Exception as e:
        return {"events": [], "error": f"Search failed: {e}"}

    if not web_results:
        return {"events": [], "message": "No search results found"}

    context = "\n\n".join(
        f"Source: {r.get('url')}\nTitle: {r.get('title')}\nContent: {r.get('content', '')[:500]}"
        for r in web_results
    )
    extraction_prompt = f"""Extract timestamped events from these search results about: {query}

{context}

Return a JSON array of events:
[{{"date": "2026-01-15" or null, "title": "...", "description": "...", "source": "https://..."}}]
Only return valid JSON array, no extra text."""

    try:
        response = client.chat.completions.create(
            model=DEFAULT_MODEL,
            messages=[
                {"role": "system", "content": "You extract timestamped events from search results. Return only valid JSON."},
                {"role": "user", "content": extraction_prompt},
            ],
            temperature=0.3,
            max_tokens=1500,
        )
        events = json.loads(response.choices[0].message.content.strip())
        return {"events": events, "search_results_count": len(web_results)}
    except Exception as e:
        return {"events": [], "error": f"Event extraction failed: {e}", "search_results_count": len(web_results)}


# Terminal tool: records a brand-new-issue decision. Does NOT write to the database.
def _tool_draft_create_issue(
    title: str,
    summary: str,
    why: str,
    tags: list[str] | None,
    research_dossier: str,
) -> dict[str, Any]:
    return {
        "status": "drafted",
        "candidate": {
            "decision": "create",
            "title": title,
            "summary": summary,
            "why": why,
            "tags": tags or [],
            "research_dossier": research_dossier,
        },
    }


# Terminal tool: records a merge-into-existing-issue decision. Does NOT write to the database.
def _tool_draft_merge_issue(issue_id: str, additional_info: str, reason: str) -> dict[str, Any]:
    return {
        "status": "drafted",
        "candidate": {
            "decision": "merge",
            "issue_id": issue_id,
            "additional_info": additional_info,
            "reason": reason,
            "research_dossier": additional_info,
        },
    }


TOOLS = [
    {
        "type": "function",
        "function": {
            "name": "search_tavily",
            "description": "Fast web search for initial exploration and verification.",
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {"type": "string"},
                    "max_results": {"type": "integer", "minimum": 1, "maximum": 10},
                },
                "required": ["query"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "search_perplexity",
            "description": "Deep research search with citations (higher quality, slower).",
            "parameters": {
                "type": "object",
                "properties": {"query": {"type": "string"}},
                "required": ["query"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "list_issues",
            "description": "List current issues to understand existing coverage.",
            "parameters": {"type": "object", "properties": {}},
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_issue",
            "description": "Inspect a specific existing issue by id.",
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
            "name": "check_similar_issues",
            "description": "Check semantic similarity of a candidate against existing issues (0-1, higher = more similar).",
            "parameters": {
                "type": "object",
                "properties": {
                    "candidate_text": {"type": "string"},
                    "top_k": {"type": "integer", "minimum": 1, "maximum": 10},
                },
                "required": ["candidate_text"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "collect_events",
            "description": "Search for and extract timestamped events (announcements, incidents, milestones) related to a query.",
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {"type": "string"},
                    "max_results": {"type": "integer", "minimum": 1, "maximum": 10},
                },
                "required": ["query"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "draft_create_issue",
            "description": "Record a draft for a brand-new issue (similarity < 0.9 to anything existing). Ends the research loop.",
            "parameters": {
                "type": "object",
                "properties": {
                    "title": {"type": "string"},
                    "summary": {"type": "string"},
                    "why": {"type": "string"},
                    "tags": {"type": "array", "items": {"type": "string"}},
                    "research_dossier": {
                        "type": "string",
                        "description": "Consolidated research findings: evidence, context, and sources gathered for this issue.",
                    },
                },
                "required": ["title", "summary", "why", "research_dossier"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "draft_merge_issue",
            "description": "Record a draft to merge into an existing issue (similarity >= 0.9). Ends the research loop.",
            "parameters": {
                "type": "object",
                "properties": {
                    "issue_id": {"type": "string"},
                    "additional_info": {"type": "string"},
                    "reason": {"type": "string"},
                },
                "required": ["issue_id", "additional_info", "reason"],
            },
        },
    },
]

_TERMINAL_TOOLS = {"draft_create_issue", "draft_merge_issue"}


def _dispatch_tool(name: str, arguments: dict[str, Any]) -> dict[str, Any]:
    if name == "search_tavily":
        return _tool_search_tavily(arguments["query"], int(arguments.get("max_results", 10)))
    if name == "search_perplexity":
        return _tool_search_perplexity(arguments["query"])
    if name == "list_issues":
        return _tool_list_issues()
    if name == "get_issue":
        return _tool_get_issue(arguments["issue_id"])
    if name == "check_similar_issues":
        return _tool_check_similar_issues(arguments["candidate_text"], int(arguments.get("top_k", 5)))
    if name == "collect_events":
        return _tool_collect_events(arguments["query"], int(arguments.get("max_results", 10)))
    if name == "draft_create_issue":
        return _tool_draft_create_issue(
            arguments["title"],
            arguments["summary"],
            arguments.get("why", ""),
            arguments.get("tags"),
            arguments.get("research_dossier", ""),
        )
    if name == "draft_merge_issue":
        return _tool_draft_merge_issue(
            arguments["issue_id"], arguments["additional_info"], arguments.get("reason", "")
        )
    raise ValueError(f"Unknown tool: {name}")


def discover_and_research(
    topic: str = "",
    instruction: str = "",
    max_iterations: int = 6,
    memory_context: str = "",
    judge_feedback: str = "",
) -> dict[str, Any]:
    """Run the bounded discover+research loop and return a draft (never persists).

    Args:
        topic: Optional focus area hint. If empty, explores autonomously.
        instruction: Optional strategic guidance.
        max_iterations: Max tool-calling iterations before giving up.
        memory_context: Optional context from prior runs (RAG memory, leaderboard, etc).
        judge_feedback: Feedback from a prior rejected judge verdict, fed back in for a retry.

    Returns:
        Dict with keys: candidate (dict or None), research_content (str), events (list),
        trace (list), iterations (int), final_message (str).
    """
    topic = topic.strip()
    instruction = instruction.strip() or (
        f"Explore {topic} and find one specific, evidence-backed issue worth tracking."
        if topic
        else "Autonomously explore any domain and find one specific, evidence-backed issue worth tracking."
    )

    if not search_service.is_configured():
        raise RuntimeError("Tavily API key not configured. Please add TAVILY_API_KEY to your .env file.")

    user_content = (
        f"Focus: {topic if topic else 'Autonomous exploration'}\n"
        f"Strategy: {instruction}\n\n"
        f"Memory context:\n{memory_context or 'No prior memory'}\n"
    )
    if judge_feedback:
        user_content += (
            f"\nA previous attempt was REJECTED by quality review with this feedback:\n"
            f"{judge_feedback}\n"
            f"Address this feedback before drafting again.\n"
        )

    messages: list[dict[str, Any]] = [
        {"role": "system", "content": SYSTEM_PROMPT},
        {"role": "user", "content": user_content},
    ]

    trace: list[dict[str, Any]] = []
    events_collected: list[dict[str, Any]] = []
    candidate: dict[str, Any] | None = None
    final_message = ""

    agent_span = langfuse.start_observation(
        as_type="agent",
        name="discover_and_research",
        input={"topic": topic, "instruction": instruction, "max_iterations": max_iterations},
    )

    try:
        for iteration in range(max_iterations):
            response = client.chat.completions.create(
                model=DEFAULT_MODEL,
                messages=messages,
                tools=TOOLS,
                tool_choice="auto",
                temperature=0.2,
                max_tokens=1200,
            )
            assistant_message = response.choices[0].message
            assistant_payload: dict[str, Any] = {"role": "assistant", "content": assistant_message.content or ""}
            if assistant_message.tool_calls:
                assistant_payload["tool_calls"] = [
                    tc.model_dump() if hasattr(tc, "model_dump") else tc for tc in assistant_message.tool_calls
                ]
            messages.append(assistant_payload)

            if not assistant_message.tool_calls:
                final_message = assistant_message.content or ""
                break

            for tool_call in assistant_message.tool_calls:
                tool_name = tool_call.function.name
                tool_arguments = json.loads(tool_call.function.arguments or "{}")

                with agent_span.start_as_current_observation(
                    as_type="tool", name=tool_name, input=tool_arguments
                ) as tool_span:
                    try:
                        tool_result = _dispatch_tool(tool_name, tool_arguments)
                        tool_span.update(output=tool_result)
                    except Exception as exc:
                        tool_span.update(level="ERROR", status_message=str(exc))
                        raise

                trace.append({"iteration": iteration + 1, "tool": tool_name, "arguments": tool_arguments, "result": tool_result})

                if tool_name == "collect_events" and isinstance(tool_result.get("events"), list):
                    events_collected.extend(tool_result["events"])

                if tool_name in _TERMINAL_TOOLS and isinstance(tool_result.get("candidate"), dict):
                    candidate = tool_result["candidate"]
                    final_message = f"Drafted candidate via {tool_name}."

                messages.append({"role": "tool", "tool_call_id": tool_call.id, "content": json.dumps(tool_result)})

            if candidate is not None:
                break
    except Exception as exc:
        agent_span.update(level="ERROR", status_message=str(exc))
        raise
    finally:
        agent_span.update(output={"candidate": candidate, "events_count": len(events_collected), "final_message": final_message})
        agent_span.end()

    research_content = (candidate or {}).get("research_dossier", "")

    return {
        "topic": topic,
        "instruction": instruction,
        "candidate": candidate,
        "research_content": research_content,
        "events": events_collected,
        "trace": trace,
        "iterations": len(trace),
        "final_message": final_message,
    }
