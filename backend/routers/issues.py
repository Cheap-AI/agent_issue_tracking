from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException

from sqlalchemy.orm import Session

from backend.core.db import get_db
from backend.core.issue import create_issue as create_issue_in_db, delete_issue as delete_issue_db, get_issue, list_events_for_issue, list_issues
from backend.core.knowledge import update_component
from backend.models.schemas import IssueCreateRequest, UpdateComponentRequest
from backend.workflows.collect_events import collect_events_for_issue
from backend.workflows.update_issue import quick_update

router = APIRouter()


@router.get("/api/issues")
def get_issues(
    year: int | None = None,
    month: int | None = None,
    session: Session = Depends(get_db),
) -> dict[str, object]:
    """저장된 이슈 목록을 반환합니다. Optional year/month query params filter by target_year/target_month."""
    return {"issues": list_issues(session=session, target_year=year, target_month=month)}


@router.post("/api/issues", status_code=201)
def create_issue_endpoint(
    payload: IssueCreateRequest,
    session: Session = Depends(get_db),
) -> dict[str, object]:
    """새로운 이슈를 생성합니다."""
    if not payload.title.strip():
        raise HTTPException(status_code=400, detail="Title is required")

    issue = create_issue_in_db(
        payload.title,
        payload.summary,
        payload.why,
        payload.tags,
        target_year=payload.target_year,
        target_month=payload.target_month,
        session=session,
    )
    return {"issue": issue}


@router.get("/api/issues/{issue_id}")
def get_issue_endpoint(issue_id: str, session: Session = Depends(get_db)) -> dict[str, object]:
    """단일 이슈를 조회합니다."""
    issue = get_issue(issue_id, session=session)
    if issue is None:
        raise HTTPException(status_code=404, detail="Issue not found")
    return {"issue": issue}


@router.delete("/api/issues/{issue_id}")
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


@router.post("/api/issues/{issue_id}/components/{component}")
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


@router.post("/api/issues/{issue_id}/research")
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


@router.get("/api/issues/{issue_id}/events")
def get_issue_events(issue_id: str, session: Session = Depends(get_db)) -> dict[str, object]:
    """Get events for an issue in chronological order (oldest first)."""
    issue = get_issue(issue_id, session=session)
    if issue is None:
        raise HTTPException(status_code=404, detail="Issue not found")

    events = list_events_for_issue(issue_id, session=session)
    return {"issue_id": issue_id, "events": events, "count": len(events)}


@router.post("/api/issues/{issue_id}/events")
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
