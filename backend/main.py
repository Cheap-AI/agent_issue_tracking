from dotenv import load_dotenv

load_dotenv()

from backend.telemetry import setup_langfuse, instrument_app

langfuse_client = setup_langfuse()  # before any get_client() at import time below

import logging
import sys
from contextlib import asynccontextmanager
from fastapi import Depends, FastAPI
from fastapi.middleware.cors import CORSMiddleware

# Configure logging to stdout so we can see it in the terminal
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[logging.StreamHandler(sys.stdout)]
)
logger = logging.getLogger(__name__)

from backend.core.auth import CurrentUser, get_current_user
from backend.routers import agentic, chat, discovery, issues, reports

# FastAPI 앱을 생성합니다.
@asynccontextmanager
async def lifespan(_app: FastAPI):
    yield
    langfuse_client.shutdown()  # flush buffered traces on redeploy/restart


app = FastAPI(title="Issue Tracking API", lifespan=lifespan)  # python -m uvicorn backend.main:app --reload
instrument_app(app)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "https://agent-issue-tracking.vercel.app",
        "https://agent-issue-tracking-329tizkp8-cheap-ai-5675s-projects.vercel.app",
        "http://localhost:3000",
        "http://127.0.0.1:3000",
    ],
    allow_origin_regex=r"https://agent-issue-tracking.*\.vercel\.app",
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)



@app.get("/")
def root() -> dict[str, object]:
    """Root route so platform health checks hitting '/' don't 404."""
    return {"status": "ok", "service": "python-fastapi"}


@app.get("/api/health")
def health_check() -> dict[str, object]:
    """Next.js 프론트엔드가 연결을 확인할 수 있는 간단한 헬스 체크 엔드포인트입니다."""
    return {
        "status": "ok",
        "service": "python-fastapi",
        "message": "Backend is running",
    }


@app.get("/api/me")
def me(user: CurrentUser = Depends(get_current_user)) -> dict[str, object]:
    """The signed-in user's profile (creates it on first login)."""
    return {"id": user.id, "email": user.email, "role": user.role}


for _router in (issues.router, discovery.router, reports.router, chat.router, agentic.router):
    app.include_router(_router)
