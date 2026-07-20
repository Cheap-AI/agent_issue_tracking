from typing import Any

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from api.database import create_issue as create_issue_in_db, init_db, list_issues

# FastAPI 앱을 생성합니다.
app = FastAPI(title="Issue Tracking API") #python -m uvicorn api.index:app --reload

init_db()

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

class IssueCreateRequest(BaseModel):
    title: str
    summary: str


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


class AgentRequest(BaseModel):
    topic: str


@app.post("/api/agent/research")
def research_topic(payload: AgentRequest) -> dict[str, object]:
    """Create a simple research draft for a topic before connecting Tavily and OpenAI."""
    topic = payload.topic.strip()
    if not topic:
        raise HTTPException(status_code=400, detail="Topic is required")

    summary = (
        f"Research draft for '{topic}': "
        f"Start by gathering key facts, identify the main stakeholders, and note any open questions. "
        "This draft is a placeholder until external search and LLM summarization are wired in."
    )

    return {
        "topic": topic,
        "status": "ready",
        "summary": summary,
        "sources": [],
    }
