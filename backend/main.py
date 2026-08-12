from dotenv import load_dotenv

load_dotenv()

import logging
import sys
from fastapi import FastAPI, HTTPException, BackgroundTasks, Depends
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session

# Configure logging to stdout so we can see it in the terminal
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[logging.StreamHandler(sys.stdout)]
)
logger = logging.getLogger(__name__)

from backend.core.issue import create_issue as create_issue_in_db, get_issue, list_issues, delete_issue as delete_issue_db
from backend.core.knowledge import update_component
from backend.core.db import get_db
from backend.models.schemas import AgentRequest, DiscoveryRequest, IssueCreateRequest, UpdateComponentRequest
from backend.workflows.discover_issue import discover_issue as discover_issue_workflow
from backend.workflows.update_issue import update_issue_workflow, quick_update
from backend.workflows.collect_events import collect_events_for_issue
from backend.workflows.discovery_reports import load_recent_reports, get_discovery_insights
from backend.agents.ranking.agent import get_leaderboard
from backend.services import search_service

# FastAPI 앱을 생성합니다.
app = FastAPI(title="Issue Tracking API")  # python -m uvicorn backend.main:app --reload

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "https://agent-issue-tracking.vercel.app",
        "https://agent-issue-tracking-329tizkp8-cheap-ai-5675s-projects.vercel.app",
        "http://localhost:3000",
        "http://127.0.0.1:3000",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/api/health")
def health_check() -> dict[str, object]:
    """Next.js 프론트엔드가 연결을 확인할 수 있는 간단한 헬스 체크 엔드포인트입니다."""
    return {
        "status": "ok",
        "service": "python-fastapi",
        "message": "Backend is running",
    }


@app.get("/api/issues")
def get_issues(session: Session = Depends(get_db)) -> dict[str, object]:
    """저장된 이슈 목록을 반환합니다."""
    return {"issues": list_issues(session=session)}


@app.post("/api/issues", status_code=201)
def create_issue_endpoint(
    payload: IssueCreateRequest,
    session: Session = Depends(get_db),
) -> dict[str, object]:
    """새로운 이슈를 생성합니다."""
    if not payload.title.strip():
        raise HTTPException(status_code=400, detail="Title is required")

    issue = create_issue_in_db(payload.title, payload.summary, payload.why, payload.tags, session=session)
    return {"issue": issue}


@app.get("/api/issues/{issue_id}")
def get_issue_endpoint(issue_id: str, session: Session = Depends(get_db)) -> dict[str, object]:
    """단일 이슈를 조회합니다."""
    issue = get_issue(issue_id, session=session)
    if issue is None:
        raise HTTPException(status_code=404, detail="Issue not found")
    return {"issue": issue}


@app.delete("/api/issues/{issue_id}")
def delete_issue_endpoint(issue_id: str, session: Session = Depends(get_db)) -> dict[str, object]:
    """Delete an issue by id."""
    deleted = delete_issue_db(issue_id, session=session)
    if not deleted:
        raise HTTPException(status_code=404, detail="Issue not found")
    return {
        "issue_id": issue_id,
        "status": "deleted",
        "message": f"Issue {issue_id} has been deleted"
    }


@app.post("/api/issues/{issue_id}/components/{component}")
def update_issue_component(
    issue_id: str,
    component: str,
    payload: UpdateComponentRequest,
    background_tasks: BackgroundTasks,
    session: Session = Depends(get_db),
) -> dict[str, object]:
    """Update an issue component with background embedding generation.
    
    This endpoint demonstrates FastAPI's BackgroundTasks pattern:
    - Response is sent immediately after saving content
    - Embeddings are generated in background using FastAPI's thread pool
    - API remains responsive during embedding generation
    """
    # Verify issue exists
    issue = get_issue(issue_id, session=session)
    if issue is None:
        raise HTTPException(status_code=404, detail="Issue not found")
    
    # Valid component types
    valid_components = ["research", "summary", "timeline", "sources", "questions"]
    if component not in valid_components:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid component. Must be one of: {', '.join(valid_components)}"
        )
    
    # Save component and queue background task for embeddings
    version = update_component(
        issue_id=issue_id,
        component=component,
        new_content=payload.content,
        background_tasks=background_tasks  # FastAPI injects this!
    )
    
    # Response is sent immediately, embeddings happen in background
    return {
        "issue_id": issue_id,
        "component": component,
        "version": version,
        "status": "saved",
        "embeddings": "generating in background"
    }


@app.post("/api/issues/{issue_id}/research")
def trigger_research_workflow(
    issue_id: str,
    background_tasks: BackgroundTasks,
    search_query: str | None = None,
    session: Session = Depends(get_db),
) -> dict[str, object]:
    """Trigger the complete research → summary → ranking workflow.
    
    This endpoint runs all three agents in sequence:
    1. Research Agent: Conducts research using RAG + Tavily
    2. Summary Agent: Generates executive summary
    3. Ranking Agent: Scores issue and updates leaderboard
    
    The workflow runs in the background.
    """
    # Verify issue exists
    issue = get_issue(issue_id, session=session)
    if issue is None:
        raise HTTPException(status_code=404, detail="Issue not found")
    
    # Use issue title as search query if not provided
    if not search_query:
        search_query = issue["title"]
    
    # Queue the complete workflow in background
    background_tasks.add_task(
        quick_update,
        issue_id=issue_id,
        search_query=search_query
    )
    
    return {
        "issue_id": issue_id,
        "search_query": search_query,
        "status": "workflow started",
        "message": "Research → Summary → Ranking agents running in background"
    }


@app.post("/api/issues/{issue_id}/events")
def trigger_events_collection(
    issue_id: str,
    background_tasks: BackgroundTasks,
    search_query: str | None = None,
    session: Session = Depends(get_db),
) -> dict[str, object]:
    """Trigger event collection for an issue in the background.
    
    This endpoint searches for and extracts timestamped events related to an issue,
    then stores them in the events table for timeline construction.
    """
    issue = get_issue(issue_id, session=session)
    if issue is None:
        raise HTTPException(status_code=404, detail="Issue not found")
    
    background_tasks.add_task(
        collect_events_for_issue,
        issue_id=issue_id,
        search_query=search_query,
        max_results=10
    )
    
    return {
        "issue_id": issue_id,
        "status": "events collection started",
        "message": "Events collection running in background"
    }


@app.post("/api/issues/{issue_id}/research")
def trigger_research_workflow(
    issue_id: str,
    background_tasks: BackgroundTasks,
    search_query: str | None = None,
    session: Session = Depends(get_db),
) -> dict[str, object]:
    """Trigger the complete research → summary → ranking workflow.
    
    This endpoint runs all three agents in sequence:
    1. Research Agent: Conducts research using RAG + Tavily
    2. Summary Agent: Generates executive summary
    3. Ranking Agent: Scores issue and updates leaderboard
    
    The workflow runs in the background.
    """
    # Verify issue exists
    issue = get_issue(issue_id, session=session)
    if issue is None:
        raise HTTPException(status_code=404, detail="Issue not found")
    
    # Use issue title as search query if not provided
    if not search_query:
        search_query = issue["title"]
    
    # Queue the complete workflow in background
    background_tasks.add_task(
        quick_update,
        issue_id=issue_id,
        search_query=search_query
    )
    
    return {
        "issue_id": issue_id,
        "search_query": search_query,
        "status": "workflow started",
        "message": "Research → Summary → Ranking agents running in background"
    }


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


@app.post("/api/discovery")
def trigger_discovery_workflow(
    payload: DiscoveryRequest,
    background_tasks: BackgroundTasks,
) -> dict[str, object]:
    """Trigger the bounded discovery agent in the background.
    
    The agent can run in autonomous mode (no topic) or with an optional topic hint.
    """
    topic = payload.topic.strip()
    # No longer require topic - autonomous exploration is supported
    
    print(f"DEBUG: Discovery endpoint hit! topic={topic}")
    sys.stdout.flush()
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


@app.get("/api/leaderboard")
def get_leaderboard_endpoint(limit: int = 50) -> dict[str, object]:
    """Get the top-N issues leaderboard.
    
    Returns issues sorted by overall_score with their rankings.
    """
    leaderboard = get_leaderboard(limit=limit)
    return {
        "leaderboard": leaderboard,
        "count": len(leaderboard)
    }


@app.get("/api/discovery/reports")
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


@app.get("/api/discovery/insights")
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


@app.post("/api/agent/research")
def research_topic(payload: AgentRequest) -> dict[str, object]:
    """Search for a topic using Tavily and return a summary of findings (stateless, not persisted)."""
    topic = payload.topic.strip()
    if not topic:
        raise HTTPException(status_code=400, detail="Topic is required")

    if not search_service.is_configured():
        return {
            "topic": topic,
            "status": "error",
            "summary": "Tavily API key not configured. Please add TAVILY_API_KEY to your .env file.",
            "sources": [],
        }

    try:
        results = search_service.search(topic, max_results=5)
    except Exception as e:
        return {
            "topic": topic,
            "status": "error",
            "summary": f"Search failed: {str(e)}",
            "sources": [],
        }

    if not results:
        return {
            "topic": topic,
            "status": "no_results",
            "summary": "No search results found for this topic.",
            "sources": [],
        }

    summary = f"Search findings for '{topic}':\n\n"
    for res in results[:3]:
        summary += f"- {res.get('content', '')[:200]}...\n"

    return {
        "topic": topic,
        "status": "completed",
        "summary": summary,
        "sources": [res.get("url", "") for res in results],
    }
