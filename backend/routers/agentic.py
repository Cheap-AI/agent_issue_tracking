from fastapi import APIRouter, Depends, HTTPException

from uuid import uuid4

from backend.core.auth import get_current_user
from backend.core.rate_limit import rate_limit
from backend.models.schemas import AgentRequest, AgenticPipelineResumeRequest, AgenticPipelineStartRequest
from backend.services import search_service
from backend.workflows.langgraph_agentic_pipeline import get_pipeline_state, resume_pipeline, start_pipeline

router = APIRouter()


@router.post("/api/agentic-pipeline/start", dependencies=[Depends(rate_limit("agentic_start", 5, 3600))])
def start_agentic_pipeline(payload: AgenticPipelineStartRequest) -> dict[str, object]:
    """Start a discover_research -> summarize_rank -> human_review -> persist run.

    Runs synchronously up to the first pause (human_review) or a rejected end state -
    the underlying agent loop is already a background-safe call, no BackgroundTasks needed.
    """
    thread_id = str(uuid4())
    return start_pipeline(thread_id, topic=payload.topic.strip(), instruction=payload.instruction.strip())


@router.get("/api/agentic-pipeline/{thread_id}", dependencies=[Depends(get_current_user)])
def get_agentic_pipeline_status(thread_id: str) -> dict[str, object]:
    """Get a pipeline run's current status, including the pending human-review payload if any."""
    return get_pipeline_state(thread_id)


@router.post("/api/agentic-pipeline/{thread_id}/resume", dependencies=[Depends(rate_limit("agentic_resume", 20, 3600))])
def resume_agentic_pipeline(thread_id: str, payload: AgenticPipelineResumeRequest) -> dict[str, object]:
    """Resume a paused run with a human decision ('approve' persists the draft, 'reject' discards it)."""
    if payload.decision not in ("approve", "reject"):
        raise HTTPException(status_code=400, detail="decision must be 'approve' or 'reject'")
    return resume_pipeline(thread_id, decision=payload.decision, feedback=payload.feedback)


@router.post("/api/agent/research", dependencies=[Depends(rate_limit("quick_research", 10, 60))])
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
