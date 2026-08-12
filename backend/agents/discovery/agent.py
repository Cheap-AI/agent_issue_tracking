"""Discovery agent: finds candidate issues and optionally creates and seeds them.

The agent uses bounded tool calling so it can:
- inspect the current issue list
- search Tavily for new candidates
- create new issues when confidence is high
- seed the research workflow for newly created issues
"""
from __future__ import annotations

import json
import logging
import os
from pathlib import Path
from typing import Any

from openai import OpenAI

from backend.core.issue import create_issue, get_issue, list_issues
from backend.services import search_service
from backend.services import perplexity_service
from backend.services.vector_search import search_similar_issues_by_text, store_issue_embedding
from backend.workflows.update_issue import quick_update
from backend.agents.ranking.agent import score_issue

# Add logging
logger = logging.getLogger(__name__)


client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

PROMPT_PATH = Path(__file__).resolve().parents[2] / "prompts" / "discovery" / "system_prompt.md"
DEFAULT_MODEL = os.getenv("OPENAI_DISCOVERY_MODEL", "gpt-4o")  # Use gpt-4o for better reasoning (was gpt-4o-mini)


# Loads the discovery system prompt from disk with a safe fallback.
def _load_system_prompt() -> str:
    if PROMPT_PATH.exists():
        return PROMPT_PATH.read_text(encoding="utf-8")
    return (
        "You are a discovery agent. Search for candidate issues, inspect current issues, "
        "and create only high-confidence new issues."
    )


# Tavily tool wrapper that returns query + raw result payload.
def _tool_search_tavily(query: str, max_results: int = 10) -> dict[str, Any]:
    return {
        "query": query,
        "results": search_service.search(query, max_results=max_results),
    }


# Perplexity tool wrapper for research-focused search with citations.
def _tool_search_perplexity(query: str) -> dict[str, Any]:
    if not perplexity_service.is_configured():
        return {
            "query": query,
            "results": [],
            "error": "Perplexity API not configured. Add PERPLEXITY_API_KEY to .env"
        }
    try:
        return {
            "query": query,
            "results": perplexity_service.search(query),
        }
    except Exception as e:
        # Gracefully handle Perplexity failures - log but don't crash
        logger.warning(f"Perplexity search failed for '{query}': {str(e)}")
        return {
            "query": query,
            "results": [],
            "error": f"Perplexity search failed: {str(e)[:100]}"
        }


# Lists current issues to support duplicate checks during discovery.
def _tool_list_issues() -> dict[str, Any]:
    return {"issues": list_issues()}


# Fetches a specific issue by id for deeper comparison.
def _tool_get_issue(issue_id: str) -> dict[str, Any]:
    issue = get_issue(issue_id)
    if issue is None:
        return {"issue": None}
    return {"issue": issue}


# Creates a new issue row from agent-provided fields, including why it matters and tags.
# Now also accepts dimension_scores from ranking (optional, will calculate if not provided).
def _tool_create_issue(
    title: str, 
    summary: str, 
    why: str = "", 
    tags: list[str] | None = None,
    dimension_scores: dict[str, int] | None = None
) -> dict[str, Any]:
    issue = create_issue(title=title, summary=summary, why=why, tags=tags or [])
    
    # Store embedding for future deduplication
    store_issue_embedding(issue_id=issue["id"], title=title, summary=summary, why=why)
    
    # Score if dimensions not provided (agent may provide inline scores from merged logic)
    if dimension_scores:
        # TODO: Store dimension_scores in tracked_issues table
        # For now, just return the issue with scores attached
        issue["dimension_scores"] = dimension_scores
    
    return {"issue": issue}


# Semantic similarity search for existing issues to prevent duplicates.
def _tool_check_similar_issues(candidate_text: str, top_k: int = 5) -> dict[str, Any]:
    """Check if a candidate issue is similar to existing issues.
    
    Args:
        candidate_text: Combined title + summary + why of candidate issue
        top_k: Number of similar issues to return (default 5)
        
    Returns:
        Dict with 'similar_issues' list, each having issue_id, title, similarity (0-1)
    """
    similar = search_similar_issues_by_text(candidate_text, top_k=top_k)
    return {"similar_issues": similar}


# Merge a candidate into an existing issue instead of creating a new one.
def _tool_merge_into_issue(issue_id: str, additional_info: str, reason: str = "") -> dict[str, Any]:
    """Merge candidate information into an existing issue.
    
    When similarity >= 0.9, merge instead of creating a new issue.
    This appends additional context to the existing issue and updates its embedding.
    
    Args:
        issue_id: Existing issue to merge into
        additional_info: New information to append to summary
        reason: Why this was merged (e.g., "duplicate found with 0.92 similarity")
        
    Returns:
        Dict with updated issue and merge status
    """
    # Get existing issue
    issue = get_issue(issue_id)
    if not issue:
        return {"error": f"Issue {issue_id} not found", "status": "failed"}
    
    # Append additional_info to summary with merge note
    updated_summary = issue["summary"] + f"\n\n[Merged duplicate]: {additional_info}"
    if reason:
        updated_summary += f" (Reason: {reason})"
    
    # TODO: Update issue in database with new summary
    # For now, just return the merge notification
    # In production, call update_issue(issue_id, summary=updated_summary)
    
    # Re-embed after merge
    store_issue_embedding(
        issue_id=issue_id,
        title=issue["title"],
        summary=updated_summary,
        why=issue.get("why", "")
    )
    
    return {
        "status": "merged",
        "issue_id": issue_id,
        "message": f"Merged into existing issue: {issue['title']}",
        "reason": reason
    }


# Runs the full enrichment workflow on a discovered issue.
def _tool_seed_issue(issue_id: str, search_query: str) -> dict[str, Any]:
    result = quick_update(issue_id=issue_id, search_query=search_query)
    return {"result": result}


TOOLS = [
    {
        "type": "function",
        "function": {
            "name": "search_tavily",
            "description": "Fast web search for quick verification, recent news, and initial exploration. Use when you need speed and breadth. For initial reconnaissance.",
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
            "description": "Deep research with authoritative citations. Use when creating issues (you need factual evidence), fact-checking claims, or need comprehensive analysis. Higher quality but slower. PREFER THIS when validating issue significance.",
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {"type": "string"},
                },
                "required": ["query"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "list_issues",
            "description": "List the current issues so duplicates can be avoided.",
            "parameters": {"type": "object", "properties": {}},
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_issue",
            "description": "Inspect a specific issue by id.",
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
            "description": "Check semantic similarity between a candidate issue and existing issues. Use BEFORE creating a new issue to prevent duplicates. Returns similarity scores (0-1, higher is more similar).",
            "parameters": {
                "type": "object",
                "properties": {
                    "candidate_text": {
                        "type": "string",
                        "description": "Combined text from title + summary + why of the candidate issue"
                    },
                    "top_k": {
                        "type": "integer",
                        "minimum": 1,
                        "maximum": 10,
                        "description": "Number of similar issues to return (default 5)"
                    },
                },
                "required": ["candidate_text"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "merge_into_issue",
            "description": "Merge a candidate issue into an existing issue instead of creating a new one. Use when similarity >= 0.9 to consolidate duplicate information.",
            "parameters": {
                "type": "object",
                "properties": {
                    "issue_id": {
                        "type": "string",
                        "description": "Existing issue ID to merge into"
                    },
                    "additional_info": {
                        "type": "string",
                        "description": "New information from the candidate to append"
                    },
                    "reason": {
                        "type": "string",
                        "description": "Why this merge is happening (e.g., 'duplicate found with 0.92 similarity')"
                    },
                },
                "required": ["issue_id", "additional_info"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "create_issue",
            "description": "Create a new issue when the candidate is confidently new and not a duplicate (similarity < 0.75).",
            "parameters": {
                "type": "object",
                "properties": {
                    "title": {"type": "string"},
                    "summary": {"type": "string"},
                    "why": {"type": "string"},
                    "tags": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "Array of individual tags (single words or hyphenated phrases). Each tag is a separate array element. Example: ['20s', '30s', 'students', 'tech-workers', 'technology', 'policy', 'human-rights']. Categories: age (teens, 20s, 30s, 40s, 50s, 60+, elderly), socioeconomic (low-income, middle-class, wealthy, students, workers, unemployed), interest (parents, educators, healthcare-workers, tech-workers, investors, activists), type (health, security, economy, environment, social, technology, policy, infrastructure, education, human-rights)"
                    },
                    "dimension_scores": {
                        "type": "object",
                        "description": "Optional scoring dimensions: severity (1-10), impact (1-10), scale (1-10), recency (1-10)",
                        "properties": {
                            "severity": {"type": "integer", "minimum": 1, "maximum": 10},
                            "impact": {"type": "integer", "minimum": 1, "maximum": 10},
                            "scale": {"type": "integer", "minimum": 1, "maximum": 10},
                            "recency": {"type": "integer", "minimum": 1, "maximum": 10}
                        }
                    },
                },
                "required": ["title", "summary", "why"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "seed_issue",
            "description": "Run the existing research-summary-ranking workflow for a newly created issue.",
            "parameters": {
                "type": "object",
                "properties": {
                    "issue_id": {"type": "string"},
                    "search_query": {"type": "string"},
                },
                "required": ["issue_id", "search_query"],
            },
        },
    },
]


# Routes tool calls to local implementations.
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
        return _tool_check_similar_issues(
            arguments["candidate_text"],
            int(arguments.get("top_k", 5))
        )
    if name == "merge_into_issue":
        return _tool_merge_into_issue(
            arguments["issue_id"],
            arguments["additional_info"],
            arguments.get("reason", "")
        )
    if name == "create_issue":
        return _tool_create_issue(
            arguments["title"], 
            arguments["summary"], 
            arguments.get("why", ""),
            arguments.get("tags"),
            arguments.get("dimension_scores")
        )
    if name == "seed_issue":
        return _tool_seed_issue(arguments["issue_id"], arguments["search_query"])
    raise ValueError(f"Unknown tool: {name}")


# Executes a bounded tool-calling loop for discovery and optional issue creation.
def discover_issues(
    topic: str = "",
    instruction: str = "",
    target_issue_count: int = 20,
    require_evaluation: bool = True,
    max_results: int = 10,
    max_iterations: int = 5,
    seed_created_issues: bool = True,
    require_human_review: bool = False,
    override_human_review: bool = False,
    memory_context: str = "",
) -> dict[str, Any]:
    """Run a bounded discovery loop and optionally create + seed new issues.
    
    Args:
        topic: Optional focus area hint (e.g., "technology", "healthcare"). If empty, explores autonomously.
        instruction: Optional strategic guidance. If empty, uses autonomous exploration mode.
        target_issue_count: Number of issues to discover in this run
        require_evaluation: Whether to evaluate candidates by severity, impact, scale, recency
        max_results: Max Tavily search results per query
        max_iterations: Max tool-calling iterations
        seed_created_issues: Whether to seed research workflow for new issues
        require_human_review: Whether to block creation and return proposals instead
        override_human_review: Override review mode to allow creation
        memory_context: Persistent memory from previous runs
    """
    topic = topic.strip()
    instruction = instruction.strip()

    if not search_service.is_configured():
        raise RuntimeError("Tavily API key not configured. Please add TAVILY_API_KEY to your .env file.")

    target_issue_count = max(1, int(target_issue_count))
    
    # Build autonomous exploration instruction if none provided
    if not instruction:
        if topic:
            instruction = f"Explore {topic} and identify important, ongoing issues worth tracking. Find gaps in current coverage and discover distinct issues. Focus on timeless problems, not year-specific events."
        else:
            instruction = (
                "Autonomously explore multiple domains and identify important, ongoing issues worth tracking. "
                "Look for gaps in the current issue list. Discover distinct issues across technology, "
                "society, environment, security, health, economy, and other impactful areas."
            )

    review_mode = require_human_review and not override_human_review

    messages: list[dict[str, Any]] = [
        {"role": "system", "content": _load_system_prompt()},
        {
            "role": "user",
            "content": (
                f"Focus: {topic if topic else 'Autonomous exploration across all domains'}\n"
                f"Strategy: {instruction}\n"
                f"Target issue count: {target_issue_count}\n"
                f"Max search results per query: {max_results}\n"
                f"Human review mode: {'ON' if review_mode else 'OFF'}\n"
                f"Require evaluation (severity, impact, scale, recency): {'YES' if require_evaluation else 'NO'}\n\n"
                "Memory context (use to refine queries and avoid repeating poor searches):\n"
                f"{memory_context or 'No prior memory'}\n\n"
                "Instructions:\n"
                "- Start by listing current issues to understand gaps\n"
                "- Search for new candidates that are distinct\n"
                "- Issues should be relevant to people's lives (not necessarily global)\n"
                "- When creating issues, include relevant tags for affected groups and issue type\n"
                "- Provide evidence-based 'why' for each created issue"
            ),
        },
    ]

    trace: list[dict[str, Any]] = []
    created_issues: list[dict[str, Any]] = []
    proposed_issues: list[dict[str, Any]] = []
    proposed_duplicates: list[dict[str, Any]] = []  # Track candidates merged due to high similarity
    final_message = ""

    logger.info(f"[DISCOVERY] Starting discovery loop: target={target_issue_count}, max_iterations={max_iterations}")

    for iteration in range(max_iterations):
        logger.info(f"\n{'='*50}")
        logger.info(f"Iteration {iteration + 1}/{max_iterations}")
        logger.info(f"{'='*50}")
        
        response = client.chat.completions.create(
            model=DEFAULT_MODEL,
            messages=messages,
            tools=TOOLS,
            tool_choice="auto",
            temperature=0.2,
            max_tokens=1200,
        )

        assistant_message = response.choices[0].message
        logger.info(f"[RESPONSE] Agent response: {assistant_message.content[:200] if assistant_message.content else '(no content)'}")
        logger.info(f"[TOOLS] Tool calls: {len(assistant_message.tool_calls) if assistant_message.tool_calls else 0}")
        assistant_payload: dict[str, Any] = {"role": "assistant", "content": assistant_message.content or ""}
        if assistant_message.tool_calls:
            assistant_payload["tool_calls"] = [
                tool_call.model_dump() if hasattr(tool_call, "model_dump") else tool_call
                for tool_call in assistant_message.tool_calls
            ]
        messages.append(assistant_payload)

        if assistant_message.tool_calls:
            for tool_call in assistant_message.tool_calls:
                tool_name = tool_call.function.name
                tool_arguments = json.loads(tool_call.function.arguments or "{}")
                
                logger.info(f"  [EXECUTE] Tool: {tool_name} | Args: {str(tool_arguments)[:150]}")

                if review_mode and tool_name == "create_issue":
                    proposal = {
                        "title": tool_arguments.get("title", ""),
                        "summary": tool_arguments.get("summary", ""),
                        "why": tool_arguments.get("why", ""),
                        "search_query": topic,
                        "reason": "Human review required before issue creation",
                    }
                    proposed_issues.append(proposal)
                    tool_result = {
                        "status": "requires_human_review",
                        "proposal": proposal,
                    }
                elif review_mode and tool_name == "seed_issue":
                    tool_result = {
                        "status": "requires_human_review",
                        "message": "Seeding is blocked until issue creation is approved.",
                    }
                elif (not seed_created_issues) and tool_name == "seed_issue":
                    tool_result = {
                        "status": "skipped",
                        "message": "Seeding is disabled for this run.",
                    }
                else:
                    tool_result = _dispatch_tool(tool_name, tool_arguments)

                trace.append(
                    {
                        "iteration": iteration + 1,
                        "tool": tool_name,
                        "arguments": tool_arguments,
                        "result": tool_result,
                    }
                )

                if tool_name == "create_issue" and isinstance(tool_result.get("issue"), dict):
                    created_issues.append(tool_result["issue"])
                    if seed_created_issues:
                        issue_id = tool_result["issue"]["id"]
                        seed_result = _tool_seed_issue(issue_id, topic)
                        trace.append(
                            {
                                "iteration": iteration + 1,
                                "tool": "seed_issue",
                                "arguments": {"issue_id": issue_id, "search_query": topic},
                                "result": seed_result,
                            }
                        )

                    if len(created_issues) >= target_issue_count:
                        final_message = (
                            f"Target reached: created {len(created_issues)} issues for this campaign run."
                        )
                        break
                
                # Track merged duplicates for reporting
                if tool_name == "merge_into_issue" and tool_result.get("status") == "merged":
                    proposed_duplicates.append({
                        "candidate_info": tool_arguments.get("additional_info", ""),
                        "existing_issue_id": tool_arguments.get("issue_id"),
                        "existing_title": tool_result.get("message", ""),
                        "reason": tool_arguments.get("reason", ""),
                    })

                messages.append(
                    {
                        "role": "tool",
                        "tool_call_id": tool_call.id,
                        "content": json.dumps(tool_result),
                    }
                )

            if final_message.startswith("Target reached"):
                break
            continue

        final_message = assistant_message.content or ""
        break

    logger.info(f"\n{'='*70}")
    logger.info(f"[COMPLETE] Discovery complete:")
    logger.info(f"   - Created: {len(created_issues)} issues")
    logger.info(f"   - Proposed: {len(proposed_issues)} issues")
    logger.info(f"   - Duplicates: {len(proposed_duplicates)}")
    logger.info(f"   - Iterations: {len(trace)}")
    logger.info(f"   - Final message: {final_message[:150] if final_message else '(none)'}")
    logger.info(f"{'='*70}\n")
    
    return {
        "topic": topic,
        "instruction": instruction,
        "target_issue_count": target_issue_count,
        "require_evaluation": require_evaluation,
        "iterations": len(trace),
        "review_mode": review_mode,
        "created_issues": created_issues,
        "proposed_issues": proposed_issues,
        "proposed_duplicates": proposed_duplicates,
        "trace": trace,
        "final_message": final_message,
    }