"""Orchestration workflow: Complete issue update pipeline.

This workflow coordinates multiple agents to fully update an issue:
1. Research Agent - Conducts research with RAG + web search
2. Ranking Agent - Scores and updates leaderboard
3. Event Collection - Extracts timeline events

Note: Summary agent has been removed. Research output is the canonical knowledge.
"""
from backend.agents.researcher.agent import research_issue
from backend.agents.ranking.agent import score_issue
from backend.workflows.collect_events import collect_events_for_issue


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
    
    # Step 1: Research
    if run_research:
        research_result = research_issue(issue_id, search_query)
        results["research"] = research_result
        results["steps_completed"].append("research")
    
    # Step 2: Ranking (can run independently)
    if run_ranking:
        try:
            ranking_result = score_issue(issue_id, use_gpt=True)
            results["ranking"] = ranking_result
            results["steps_completed"].append("ranking")
        except Exception as e:
            results["ranking"] = {"error": str(e)}
    
    # Step 3: Event Collection
    if run_events:
        try:
            events_result = collect_events_for_issue(issue_id, search_query)
            results["events"] = events_result
            results["steps_completed"].append("events")
        except Exception as e:
            results["events"] = {"error": str(e)}
    
    return results


def quick_update(issue_id: str, search_query: str) -> dict:
    """Convenience function: run all agents in sequence.
    
    This is the most common workflow - research → ranking → events.
    """
    return update_issue_workflow(
        issue_id=issue_id,
        search_query=search_query,
        run_research=True,
        run_ranking=True,
        run_events=True
    )


# Legacy function for backward compatibility
def update_issue(issue_id: str) -> None:
    raise NotImplementedError("Use update_issue_workflow() or quick_update() instead.")
