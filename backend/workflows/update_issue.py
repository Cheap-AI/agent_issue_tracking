"""Orchestration workflow: Complete issue update pipeline.

This workflow coordinates multiple agents to fully update an issue:
1. Research Agent - Conducts research with RAG + web search
2. Ranking Agent - Scores and updates leaderboard
3. Event Collection - Extracts timeline events

Note: Summary agent has been removed. Research output is the canonical knowledge.
"""
from langfuse import get_client, propagate_attributes

from backend.agents.researcher.agent import research_issue
from backend.agents.ranking.agent import score_issue
from backend.workflows.collect_events import collect_events_for_issue

langfuse = get_client()


def update_issue_workflow(
    issue_id: str,
    search_query: str,
    run_research: bool = True,
    run_ranking: bool = True,
    run_events: bool = True
) -> dict:
    """Run the complete issue update workflow.
    
    Args:
        issue_id: Issue to update
        search_query: Query for research (web search)
        run_research: Whether to run research agent (default True)
        run_ranking: Whether to run ranking agent (default True)
        run_events: Whether to collect timeline events (default True)
        
    Returns:
        Dict with results from each agent that ran
    """
    results = {
        "issue_id": issue_id,
        "search_query": search_query,
        "steps_completed": []
    }

    with propagate_attributes(
        session_id=f"issue-{issue_id}",
        tags=["update_issue"],
        metadata={"issue_id": issue_id, "search_query": search_query},
    ):
        # Step 1: Research
        if run_research:
            with langfuse.start_as_current_observation(
                as_type="span", name="research", input={"issue_id": issue_id, "search_query": search_query}
            ) as span:
                try:
                    research_result = research_issue(issue_id, search_query)
                    span.update(output=research_result)
                except Exception as exc:
                    span.update(level="ERROR", status_message=str(exc))
                    raise
            results["research"] = research_result
            results["steps_completed"].append("research")

        # Step 2: Ranking (can run independently)
        if run_ranking:
            with langfuse.start_as_current_observation(
                as_type="span", name="ranking", input={"issue_id": issue_id}
            ) as span:
                try:
                    ranking_result = score_issue(issue_id, use_gpt=True)
                    span.update(output=ranking_result)
                    results["ranking"] = ranking_result
                    results["steps_completed"].append("ranking")
                except Exception as e:
                    span.update(level="ERROR", status_message=str(e))
                    results["ranking"] = {"error": str(e)}

        # Step 3: Event Collection
        if run_events:
            with langfuse.start_as_current_observation(
                as_type="span", name="events", input={"issue_id": issue_id, "search_query": search_query}
            ) as span:
                try:
                    events_result = collect_events_for_issue(issue_id, search_query)
                    span.update(output=events_result)
                    results["events"] = events_result
                    results["steps_completed"].append("events")
                except Exception as e:
                    span.update(level="ERROR", status_message=str(e))
                    results["events"] = {"error": str(e)}

    return results


def quick_update(issue_id: str, search_query: str) -> dict:
    """Convenience function: run all agents in sequence.
    
    This is the most common workflow - research → ranking → events.
    """
    try:
        return update_issue_workflow(
            issue_id=issue_id,
            search_query=search_query,
            run_research=True,
            run_ranking=True,
            run_events=True
        )
    finally:
        # Ensure buffered traces are sent since this often runs as a FastAPI BackgroundTask.
        langfuse.flush()


# Legacy function for backward compatibility
def update_issue(issue_id: str) -> None:
    raise NotImplementedError("Use update_issue_workflow() or quick_update() instead.")
