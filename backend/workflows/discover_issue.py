"""Discovery workflow for finding, creating, and seeding new issues."""
from __future__ import annotations

import json
import sys
from datetime import datetime, timezone, timedelta
from typing import Any

from sqlalchemy import text

from backend.agents.discovery.agent import discover_issues
from backend.workflows.discovery_reports import generate_report, save_report, get_discovery_insights, load_recent_reports
from backend.services.vector_search import search_similar_reports
from backend.core.db import get_session


# Counts discovery runs created in the current UTC day from Postgres.
def _runs_today() -> int:
    today_start = datetime.now(timezone.utc).date()
    tomorrow_start = today_start + timedelta(days=1)
    
    sql = """
        SELECT COUNT(*)
        FROM discovery_reports
        WHERE created_at >= :today_start AND created_at < :tomorrow_start
    """
    
    with get_session() as session:
        result = session.execute(text(sql), {
            "today_start": today_start.isoformat(),
            "tomorrow_start": tomorrow_start.isoformat()
        })
        count = result.scalar()
        return count or 0


# Builds compact memory context from semantic search over past reports.
def _build_memory_context(topic: str, instruction: str) -> str:
    """Build memory context using RAG retrieval from past discovery runs.
    
    Searches past reports semantically to recall:
    - Effective search queries for similar topics
    - Issues created in similar domains
    - Strategies that worked or failed
    
    Args:
        topic: Current discovery topic
        instruction: Current discovery instruction
        
    Returns:
        Formatted memory context string for agent
    """
    # Search for similar past runs
    query = f"{topic} {instruction}".strip() or "discovery runs"
    similar_reports = search_similar_reports(query, top_k=3)
    
    if not similar_reports:
        return "No prior discovery runs found in similar domains."
    
    context_lines = ["Past Discovery Runs (similar to current focus):", ""]
    
    for report in similar_reports:
        context_lines.append(f"- Topic: {report['topic']}")
        context_lines.append(f"  Instruction: {report['instruction']}")
        context_lines.append(f"  Findings: {len(report['findings'])} issues created")
        context_lines.append(f"  Relevant context: {report['chunk_text'][:200]}...")
        context_lines.append("")
    
    # Also load recent runs for broader context (last 5 runs)
    recent_reports = load_recent_reports(limit=5)
    if recent_reports:
        context_lines.append("Recent Discovery Activity:")
        context_lines.append("")
        for report in recent_reports[:3]:
            context_lines.append(f"- {report['metadata']['topic']}: {report['metadata']['actual_created']} issues created")
    
    return "\n".join(context_lines)


# Runs one bounded discovery execution with daily caps and RAG-based memory.
def discover_issue(
    topic: str = "",
    instruction: str = "",
    target_issue_count: int = 20,
    require_evaluation: bool = True,
    max_results: int = 10,
    max_iterations: int = 5,
    max_daily_attempts: int = 10,
    seed_created_issues: bool = True,
    require_human_review: bool = False,
    override_human_review: bool = False,
) -> dict[str, Any]:
    """Run the discovery agent with a simple daily cap and RAG-based memory.
    
    Args:
        topic: Optional focus area hint. If empty, agent explores autonomously.
        instruction: Optional strategic guidance. If empty, agent builds autonomous instruction.
        target_issue_count: Number of issues to discover (default 20)
        require_evaluation: Whether to evaluate severity/impact/scale/recency
        max_results: Max Tavily search results per query
        max_iterations: Max agent tool-calling iterations
        max_daily_attempts: Daily cap on discovery runs (default 10)
        seed_created_issues: Whether to seed research workflow for new issues
        require_human_review: Whether to block creation and return proposals
        override_human_review: Override review mode to allow creation
        
    Returns:
        Dict with created_issues, proposed_duplicates, trace, and report metadata
    """
    topic = topic.strip()
    
    # Check daily cap (set to 999 for testing - effectively unlimited)
    if _runs_today() >= max_daily_attempts and max_daily_attempts < 999:
        raise RuntimeError(f"Discovery daily cap reached ({max_daily_attempts} runs today)")
    
    # Build memory context from RAG
    memory_context = _build_memory_context(topic, instruction)
    
    started_at = datetime.now(timezone.utc).isoformat()
    result = discover_issues(
        topic=topic,
        instruction=instruction,
        target_issue_count=target_issue_count,
        require_evaluation=require_evaluation,
        max_results=max_results,
        max_iterations=max_iterations,
        seed_created_issues=seed_created_issues,
        require_human_review=require_human_review,
        override_human_review=override_human_review,
        memory_context=memory_context,
    )
    
    # Generate and save report to Postgres (with embeddings for future RAG)
    report = generate_report(result, topic, instruction)
    report_id = save_report(report)
    
    # Get aggregated insights from all past reports
    insights = get_discovery_insights()
    
    # Attach run metadata to result
    review_mode = require_human_review and not override_human_review
    result["run"] = {
        "topic": topic if topic else "autonomous",
        "instruction": instruction,
        "target_issue_count": target_issue_count,
        "require_evaluation": require_evaluation,
        "started_at": started_at,
        "finished_at": datetime.now(timezone.utc).isoformat(),
        "max_results": max_results,
        "max_iterations": max_iterations,
        "review_mode": review_mode,
        "created_issue_ids": [issue["id"] for issue in result.get("created_issues", [])],
        "proposed_issue_count": len(result.get("proposed_issues", [])),
        "proposed_duplicates_count": len(result.get("proposed_duplicates", [])),
        "trace_steps": len(result.get("trace", [])),
        "final_message": result.get("final_message", ""),
    }
    
    result["daily_cap"] = max_daily_attempts
    result["runs_today"] = _runs_today()
    result["report"] = {
        "report_id": report_id,
        "api_summary": report["api_usage"],
        "findings_count": len(report["findings"]),
        "proposed_duplicates_count": len(report.get("proposed_duplicates", [])),
        "insights": insights
    }
    
    return result


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print('Usage: python -m backend.workflows.discover_issue "<topic>"')
        sys.exit(1)
    
    created = discover_issue(" ".join(sys.argv[1:]))
    print(json.dumps(created, indent=2, default=str))