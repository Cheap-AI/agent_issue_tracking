from fastapi import APIRouter, BackgroundTasks

import logging

from backend.agents.ranking.agent import get_leaderboard
from backend.models.schemas import DiscoveryRequest
from backend.workflows.discover_issue import discover_issue as discover_issue_workflow
from backend.workflows.discovery_reports import get_discovery_insights, load_recent_reports

logger = logging.getLogger(__name__)

router = APIRouter()


def _run_discovery_with_logging(
    topic: str,
    instruction: str,
    target_issue_count: int,
    require_evaluation: bool,
    max_results: int,
    max_iterations: int,
    max_daily_attempts: int,
    seed_created_issues: bool,
    require_human_review: bool,
    override_human_review: bool,
) -> None:
    """Wrapper to run discovery with comprehensive logging."""
    logger.info("="*70)
    logger.info(f"🚀 DISCOVERY STARTED: topic='{topic or 'autonomous'}', target={target_issue_count} issues")
    logger.info(f"   Config: max_iterations={max_iterations}, seed_created_issues={seed_created_issues}")
    logger.info("="*70)
    
    try:
        result = discover_issue_workflow(
            topic=topic,
            instruction=instruction,
            target_issue_count=target_issue_count,
            require_evaluation=require_evaluation,
            max_results=max_results,
            max_iterations=max_iterations,
            max_daily_attempts=max_daily_attempts,
            seed_created_issues=seed_created_issues,
            require_human_review=require_human_review,
            override_human_review=override_human_review,
        )
        
        created_count = len(result.get("created_issues", []))
        report_id = result.get("report", {}).get("report_id")
        
        logger.info("="*70)
        logger.info(f"✅ DISCOVERY COMPLETED: Created {created_count} issues")
        logger.info(f"   Report ID: {report_id}")
        logger.info(f"   Iterations: {result.get('run', {}).get('trace_steps', 0)}")
        logger.info(f"   Message: {result.get('run', {}).get('final_message', 'N/A')[:100]}")
        logger.info("="*70)
        
    except Exception as e:
        logger.error("="*70)
        logger.error(f"❌ DISCOVERY FAILED: {type(e).__name__}: {str(e)}")
        logger.error("="*70)
        import traceback
        logger.error(traceback.format_exc())
        raise


@router.post("/api/discovery")
def trigger_discovery_workflow(
    payload: DiscoveryRequest,
    background_tasks: BackgroundTasks,
) -> dict[str, object]:
    """Trigger the bounded discovery agent in the background.
    
    The agent can run in autonomous mode (no topic) or with an optional topic hint.
    """
    topic = payload.topic.strip()
    
    logger.info(f"📥 Discovery request received: topic='{topic or 'autonomous'}', target={payload.target_issue_count}")

    background_tasks.add_task(
        _run_discovery_with_logging,
        topic=topic,
        instruction=payload.instruction,
        target_issue_count=payload.target_issue_count,
        require_evaluation=payload.require_evaluation,
        max_results=payload.max_results,
        max_iterations=payload.max_iterations,
        max_daily_attempts=payload.max_daily_attempts,
        seed_created_issues=payload.seed_created_issues,
        require_human_review=payload.require_human_review,
        override_human_review=payload.override_human_review,
    )

    return {
        "topic": topic if topic else "autonomous",
        "status": "discovery started",
        "instruction": payload.instruction,
        "target_issue_count": payload.target_issue_count,
        "require_evaluation": payload.require_evaluation,
        "max_results": payload.max_results,
        "max_iterations": payload.max_iterations,
        "max_daily_attempts": payload.max_daily_attempts,
        "seed_created_issues": payload.seed_created_issues,
        "require_human_review": payload.require_human_review,
        "override_human_review": payload.override_human_review,
    }


@router.get("/api/leaderboard")
def get_leaderboard_endpoint(limit: int = 50) -> dict[str, object]:
    """Get the top-N issues leaderboard.
    
    Returns issues sorted by overall_score with their rankings.
    """
    leaderboard = get_leaderboard(limit=limit)
    return {
        "leaderboard": leaderboard,
        "count": len(leaderboard)
    }


@router.get("/api/discovery/reports")
def get_discovery_reports(limit: int = 10) -> dict[str, object]:
    """Get recent discovery reports for RAG retrieval and analysis.
    
    Args:
        limit: Number of recent reports to load (default 10)
        
    Returns:
        List of recent discovery reports with API usage, findings, and summaries
    """
    reports = load_recent_reports(limit=limit)
    return {
        "reports": reports,
        "count": len(reports),
        "status": "success" if reports else "no reports found"
    }


@router.get("/api/discovery/insights")
def get_discovery_agent_insights() -> dict[str, object]:
    """Get aggregated insights from all past discovery runs.
    
    Returns:
        - total_reports: Number of discovery reports
        - total_issues_created: Total issues created across all runs
        - api_calls: Breakdown of Tavily vs Perplexity usage
        - average_issues_per_run: Average issues per discovery run
        - most_effective_queries: Top search queries used
        - most_common_tags: Most frequently used tags
        - api_preference: Ratio of Tavily to Perplexity usage
    """
    insights = get_discovery_insights()
    return {
        "insights": insights,
        "status": "success" if insights.get("total_reports", 0) > 0 else "no data"
    }
