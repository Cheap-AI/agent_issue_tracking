from typing import Any

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

# FastAPI 앱을 생성합니다.
app = FastAPI(title="Issue Tracking API")

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

issues_db: list[dict[str, Any]] = [
    {
        "id": 1,
        "title": "AI summary for policy updates",
        "summary": "Automatically summarize recent policy changes.",
    },
    {
        "id": 2,
        "title": "Track breaking news by topic",
        "summary": "Monitor emerging stories and flag important updates.",
    },
]


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
    return {"issues": issues_db}


@app.post("/api/issues", status_code=201)
def create_issue(payload: IssueCreateRequest) -> dict[str, object]:
    """새로운 이슈를 생성합니다."""
    if not payload.title.strip():
        raise HTTPException(status_code=400, detail="Title is required")

    issue = {
        "id": len(issues_db) + 1,
        "title": payload.title.strip(),
        "summary": payload.summary.strip(),
    }
    issues_db.append(issue)
    return {"issue": issue}
