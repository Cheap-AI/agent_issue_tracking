"""Ranking Agent - LangChain comparison variant.

Same scoring step as backend/agents/ranking/agent.py's `_score_with_gpt`, reimplemented with
LangChain (`ChatOpenAI` + `with_structured_output`) instead of the raw OpenAI SDK. This exists
purely as a side-by-side learning/comparison artifact - production still uses `score_issue()`
in agent.py. Shares the ranking config, overall-score math, and leaderboard upsert with that
module so the two implementations only differ in how the LLM call itself is made and parsed.
"""
from __future__ import annotations

import os

from langchain_openai import ChatOpenAI
from langfuse.langchain import CallbackHandler
from pydantic import BaseModel, Field

from backend.agents.ranking.agent import (
    SYSTEM_PROMPT,
    _calculate_overall_score,
    _get_ranking_config,
    upsert_tracked_issue,
)
from backend.core.db import get_session
from backend.core.knowledge import read_current
from backend.models.db_models import Issue
from sqlalchemy import select


class DimensionScores(BaseModel):
    """Structured equivalent of the JSON shape agent.py's _score_with_gpt parses manually."""

    severity: int = Field(ge=0, le=10)
    severity_reason: str
    impact: int = Field(ge=0, le=10)
    impact_reason: str
    scale: int = Field(ge=0, le=10)
    scale_reason: str
    recency: int = Field(ge=0, le=10)
    recency_reason: str


_llm = ChatOpenAI(
    model=os.getenv("OPENAI_RANKING_MODEL", "gpt-4o-mini"),
    temperature=0.3,
    api_key=os.getenv("OPENAI_API_KEY"),
).with_structured_output(DimensionScores)


def score_issue_langchain(issue_id: str, use_gpt: bool = True) -> dict:
    """LangChain-based counterpart to score_issue() - same inputs/outputs, different LLM call."""
    with get_session() as session:
        issue = session.execute(select(Issue).where(Issue.id == issue_id)).scalar_one_or_none()
        if not issue:
            raise ValueError(f"Issue {issue_id} not found")

    research = read_current(issue_id, "research")
    summary = read_current(issue_id, "summary")
    research_content = research[1] if research else issue.summary
    summary_content = summary[1] if summary else issue.summary

    if use_gpt and research_content:
        dimension_scores = _score_with_gpt_langchain(issue_id, summary_content, research_content)
    else:
        dimension_scores = {"severity": 5, "impact": 5, "scale": 5, "recency": 7}

    ranking_config = _get_ranking_config()
    overall_score = _calculate_overall_score(dimension_scores, ranking_config)
    rank = upsert_tracked_issue(issue_id, dimension_scores, overall_score, ranking_config["top_n"])

    return {
        "issue_id": issue_id,
        "dimension_scores": dimension_scores,
        "overall_score": round(overall_score, 2),
        "rank": rank,
    }


def _score_with_gpt_langchain(issue_id: str, summary: str, research: str) -> dict[str, int]:
    """Same prompt as agent.py's _score_with_gpt; no manual json.loads/.get needed here."""
    user_prompt = f"""Score this issue on four dimensions (0-10 scale):

Issue ID: {issue_id}

Summary:
{summary[:500]}...

Research (excerpt):
{research[:1500]}...

Be objective and consistent. Use the full 0-10 range appropriately."""

    try:
        result = _llm.invoke(
            [("system", SYSTEM_PROMPT), ("human", user_prompt)],
            config={"callbacks": [CallbackHandler()]},
        )
        return {
            "severity": result.severity,
            "impact": result.impact,
            "scale": result.scale,
            "recency": result.recency,
        }
    except Exception as e:
        print(f"LangChain scoring failed: {e}")
        return {"severity": 5, "impact": 5, "scale": 5, "recency": 5}
