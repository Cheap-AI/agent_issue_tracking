from pydantic import BaseModel


class IssueCreateRequest(BaseModel):
    title: str
    summary: str


class AgentRequest(BaseModel):
    topic: str
