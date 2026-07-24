from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware

from backend.core.issue import create_issue as create_issue_in_db, get_issue, list_issues
from backend.models.schemas import AgentRequest, IssueCreateRequest
from backend.services import search_service

load_dotenv()

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
def get_issues() -> dict[str, object]:
    """저장된 이슈 목록을 반환합니다."""
    return {"issues": list_issues()}


@app.post("/api/issues", status_code=201)
def create_issue_endpoint(payload: IssueCreateRequest) -> dict[str, object]:
    """새로운 이슈를 생성합니다."""
    if not payload.title.strip():
        raise HTTPException(status_code=400, detail="Title is required")

    issue = create_issue_in_db(payload.title, payload.summary)
    return {"issue": issue}


@app.get("/api/issues/{issue_id}")
def get_issue_endpoint(issue_id: str) -> dict[str, object]:
    """단일 이슈를 조회합니다."""
    issue = get_issue(issue_id)
    if issue is None:
        raise HTTPException(status_code=404, detail="Issue not found")
    return {"issue": issue}


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
