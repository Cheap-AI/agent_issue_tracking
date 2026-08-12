from pydantic import BaseModel


class IssueCreateRequest(BaseModel):
    title: str
    summary: str
    why: str = ""
    tags: list[str] = []


class AgentRequest(BaseModel):
    topic: str


class DiscoveryRequest(BaseModel):
    topic: str = ""
    instruction: str = ""
    target_issue_count: int = 20
    require_evaluation: bool = True
    max_results: int = 10
    max_iterations: int = 5
    max_daily_attempts: int = 999  # Effectively unlimited for testing
    seed_created_issues: bool = True
    require_human_review: bool = False
    override_human_review: bool = False


class UpdateComponentRequest(BaseModel):
    """Request body for updating an issue component."""
    content: str
