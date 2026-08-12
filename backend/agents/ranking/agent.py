"""Ranking Agent: Score issues and maintain top-50 leaderboard.

This agent:
1. Scores an issue on multiple dimensions (severity, impact, scale, recency)
2. Calculates overall score based on ranking configuration
3. Updates or creates tracked_issue record
4. Maintains the top-50 leaderboard by deactivating lower-ranked issues
"""
import os
from datetime import datetime

from openai import OpenAI

from backend.core.db import get_session
from backend.core.knowledge import read_current
from backend.core.global_docs import get_doc
from backend.models.db_models import TrackedIssue, Issue
from sqlalchemy import select, func
import json


# Initialize OpenAI client
client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))


SYSTEM_PROMPT = """You are a ranking agent for an AI-native Issue Intelligence Platform.

Your role is to score technology issues on multiple dimensions to maintain a curated top-50 leaderboard.

Scoring dimensions (0-10 scale):
- **Severity**: Technical severity of the issue (10 = critical vulnerability, 0 = minor)
- **Impact**: Business/user impact (10 = millions affected, 0 = minimal)
- **Scale**: Geographic/organizational reach (10 = global, 0 = single team)
- **Recency**: How current/active is this issue (10 = happening now, 0 = resolved months ago)

Provide your scoring as JSON with brief justification for each dimension."""


def score_issue(issue_id: str, use_gpt: bool = True) -> dict:
    """Score an issue and update the tracked_issues leaderboard.
    
    Args:
        issue_id: Issue to score
        use_gpt: If True, use GPT-4 for scoring. If False, use heuristics (default True)
        
    Returns:
        Dict with keys: dimension_scores, overall_score, rank
    """
    # Step 1: Get issue data
    with get_session() as session:
        issue = session.execute(
            select(Issue).where(Issue.id == issue_id)
        ).scalar_one_or_none()
        
        if not issue:
            raise ValueError(f"Issue {issue_id} not found")
    
    # Step 2: Get research and summary for context
    research = read_current(issue_id, "research")
    summary = read_current(issue_id, "summary")
    
    research_content = research[1] if research else issue.summary
    summary_content = summary[1] if summary else issue.summary
    
    # Step 3: Score using GPT-4 or heuristics
    if use_gpt and research_content:
        dimension_scores = _score_with_gpt(issue_id, summary_content, research_content)
    else:
        # Fallback heuristic scoring
        dimension_scores = {
            "severity": 5,
            "impact": 5,
            "scale": 5,
            "recency": 7  # Default to recent
        }
    
    # Step 4: Calculate overall score based on ranking config
    ranking_config = _get_ranking_config()
    overall_score = _calculate_overall_score(dimension_scores, ranking_config)
    
    # Step 5: Update or create tracked_issue record
    with get_session() as session:
        tracked = session.execute(
            select(TrackedIssue).where(TrackedIssue.issue_id == issue_id)
        ).scalar_one_or_none()
        
        if tracked:
            # Update existing
            tracked.dimension_scores = dimension_scores
            tracked.overall_score = overall_score
            tracked.last_updated_at = datetime.now()
        else:
            # Create new
            tracked = TrackedIssue(
                issue_id=issue_id,
                dimension_scores=dimension_scores,
                overall_score=overall_score,
                is_active=True,
                first_seen_at=datetime.now(),
                last_updated_at=datetime.now()
            )
            session.add(tracked)
        
        session.commit()
    
    # Step 6: Maintain top-N leaderboard
    rank = _maintain_leaderboard(ranking_config["top_n"])
    
    return {
        "issue_id": issue_id,
        "dimension_scores": dimension_scores,
        "overall_score": round(overall_score, 2),
        "rank": rank
    }


def _score_with_gpt(issue_id: str, summary: str, research: str) -> dict[str, int]:
    """Use GPT-4 to score an issue on multiple dimensions."""
    
    user_prompt = f"""Score this issue on four dimensions (0-10 scale):

Issue ID: {issue_id}

Summary:
{summary[:500]}...

Research (excerpt):
{research[:1500]}...

Provide scores as JSON:
{{
  "severity": <0-10>,
  "severity_reason": "<brief explanation>",
  "impact": <0-10>,
  "impact_reason": "<brief explanation>",
  "scale": <0-10>,
  "scale_reason": "<brief explanation>",
  "recency": <0-10>,
  "recency_reason": "<brief explanation>"
}}

Be objective and consistent. Use the full 0-10 range appropriately."""

    try:
        response = client.chat.completions.create(
            model="gpt-4o-mini",  # Changed to cheaper model that supports JSON mode
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": user_prompt}
            ],
            temperature=0.3,
            max_tokens=500,
            response_format={"type": "json_object"}
        )
        
        result = json.loads(response.choices[0].message.content)
        
        return {
            "severity": int(result.get("severity", 5)),
            "impact": int(result.get("impact", 5)),
            "scale": int(result.get("scale", 5)),
            "recency": int(result.get("recency", 5))
        }
        
    except Exception as e:
        print(f"GPT scoring failed: {e}")
        # Fallback to default scores
        return {"severity": 5, "impact": 5, "scale": 5, "recency": 5}


def _get_ranking_config() -> dict:
    """Get ranking configuration from global_docs."""
    config_str = get_doc("ranking_config")
    if config_str:
        return json.loads(config_str)
    
    # Default config
    return {
        "top_n": 50,
        "formula": "mean",
        "dimensions": ["severity", "impact", "scale", "recency"],
        "weights": {"severity": 1.0, "impact": 1.0, "scale": 1.0, "recency": 1.0}
    }


def _calculate_overall_score(dimension_scores: dict, config: dict) -> float:
    """Calculate overall score from dimension scores and config."""
    weights = config["weights"]
    formula = config.get("formula", "mean")
    
    if formula == "mean":
        # Weighted average
        total = sum(dimension_scores[dim] * weights.get(dim, 1.0) 
                   for dim in dimension_scores)
        weight_sum = sum(weights.get(dim, 1.0) for dim in dimension_scores)
        return total / weight_sum if weight_sum > 0 else 0
    
    # Could add other formulas (max, min, etc.)
    return sum(dimension_scores.values()) / len(dimension_scores)


def _maintain_leaderboard(top_n: int) -> int:
    """Maintain top-N leaderboard by deactivating lower-ranked issues.
    
    Returns the rank of the current issue (or None if not in top-N).
    """
    with get_session() as session:
        # Get all tracked issues ordered by score
        tracked_issues = session.execute(
            select(TrackedIssue)
            .order_by(TrackedIssue.overall_score.desc())
        ).scalars().all()
        
        # Mark top-N as active, rest as inactive
        for i, tracked in enumerate(tracked_issues, 1):
            tracked.is_active = (i <= top_n)
        
        session.commit()
        
        # Return rank (1-based)
        return min(len(tracked_issues), top_n)


def get_leaderboard(limit: int = 50) -> list[dict]:
    """Get the current top-N issues leaderboard.
    
    Returns list of dicts with issue info and scores.
    """
    with get_session() as session:
        results = session.execute(
            select(TrackedIssue, Issue)
            .join(Issue, TrackedIssue.issue_id == Issue.id)
            .where(TrackedIssue.is_active == True)
            .order_by(TrackedIssue.overall_score.desc())
            .limit(limit)
        ).all()
        
        leaderboard = []
        for i, (tracked, issue) in enumerate(results, 1):
            leaderboard.append({
                "rank": i,
                "issue_id": issue.id,
                "title": issue.title,
                "overall_score": round(tracked.overall_score, 2),
                "dimension_scores": tracked.dimension_scores,
                "last_updated": tracked.last_updated_at.isoformat()
            })
        
        return leaderboard
