"""Summarize & Rank agent: produces the executive summary AND importance scores together.

Merges what used to be two separate GPT calls (writer agent's generate_summary +
ranking agent's score_issue) into one structured response, since the narrative and the
dimension scores should be grounded in the same reasoning pass. Operates in DRAFT MODE:
it never writes to the database (no update_component, no TrackedIssue upsert) - it only
reads the shared ranking config to compute an overall score. Persistence happens later,
only after a human approves the draft.
"""
from __future__ import annotations

import json
import os
from typing import Any

from langfuse.openai import OpenAI

from backend.core.global_docs import get_doc

client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
DEFAULT_MODEL = os.getenv("OPENAI_SUMMARIZE_RANK_MODEL", "gpt-4o")

DEFAULT_RANKING_CONFIG = {
    "top_n": 50,
    "formula": "mean",
    "dimensions": ["severity", "impact", "scale", "recency"],
    "weights": {"severity": 1.0, "impact": 1.0, "scale": 1.0, "recency": 1.0},
}

SYSTEM_PROMPT = """You are a summarize-and-rank agent for an AI-native Issue Intelligence Platform.

Given a candidate issue and its research dossier, produce in ONE pass:
1. An executive summary (2-4 paragraphs): what the issue is, impact/severity, current status,
   and key dates if applicable. Accessible to non-technical stakeholders.
2. Dimension scores (0-10 each), each grounded in the research, not generic defaults:
   - severity: technical/substantive severity (10 = critical, 0 = minor)
   - impact: how many people/orgs affected and how much (10 = millions affected, 0 = minimal)
   - scale: geographic/organizational reach (10 = global, 0 = single team/locality)
   - recency: how current/active (10 = happening now, 0 = resolved long ago)

Respond as JSON:
{
  "summary": "...",
  "severity": <0-10>, "severity_reason": "...",
  "impact": <0-10>, "impact_reason": "...",
  "scale": <0-10>, "scale_reason": "...",
  "recency": <0-10>, "recency_reason": "..."
}"""


def _get_ranking_config() -> dict[str, Any]:
    config_str = get_doc("ranking_config")
    if config_str:
        return json.loads(config_str)
    return DEFAULT_RANKING_CONFIG


def _calculate_overall_score(dimension_scores: dict[str, int], config: dict[str, Any]) -> float:
    weights = config.get("weights", DEFAULT_RANKING_CONFIG["weights"])
    total = sum(dimension_scores[dim] * weights.get(dim, 1.0) for dim in dimension_scores)
    weight_sum = sum(weights.get(dim, 1.0) for dim in dimension_scores)
    return total / weight_sum if weight_sum > 0 else 0.0


def summarize_and_rank(
    candidate: dict[str, Any],
    research_content: str,
    events: list[dict[str, Any]],
    judge_feedback: str = "",
) -> dict[str, Any]:
    """Draft a summary + dimension scores for a candidate issue. Never persists.

    Args:
        candidate: Draft candidate dict from discover_research (title/summary/why/tags, or
            merge fields).
        research_content: Consolidated research dossier text.
        events: List of event dicts gathered during research.
        judge_feedback: Feedback from a prior rejected judge verdict, fed back in for a retry.

    Returns:
        Dict with keys: summary, dimension_scores, overall_score, rationale.
    """
    events_text = "\n".join(
        f"- {e.get('date') or 'undated'}: {e.get('title', '')} - {e.get('description', '')[:150]}"
        for e in events
    ) or "No events found."

    user_prompt = f"""Candidate issue:
{json.dumps(candidate, default=str)[:800]}

Research dossier:
{research_content[:3000]}

Events timeline:
{events_text[:1500]}"""

    if judge_feedback:
        user_prompt += (
            f"\n\nA previous attempt was REJECTED by quality review with this feedback:\n"
            f"{judge_feedback}\nAddress this feedback in your revised summary and scores."
        )

    try:
        response = client.chat.completions.create(
            model=DEFAULT_MODEL,
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": user_prompt},
            ],
            temperature=0.4,
            max_tokens=1200,
            response_format={"type": "json_object"},
        )
        result = json.loads(response.choices[0].message.content)
    except Exception as e:
        # Fallback: thin summary + neutral scores, so the pipeline/judge can still run and reject it.
        result = {
            "summary": f"Summary generation failed: {e}",
            "severity": 5, "severity_reason": "fallback",
            "impact": 5, "impact_reason": "fallback",
            "scale": 5, "scale_reason": "fallback",
            "recency": 5, "recency_reason": "fallback",
        }

    dimension_scores = {
        "severity": int(result.get("severity", 5)),
        "impact": int(result.get("impact", 5)),
        "scale": int(result.get("scale", 5)),
        "recency": int(result.get("recency", 5)),
    }
    rationale = {
        dim: result.get(f"{dim}_reason", "") for dim in dimension_scores
    }

    config = _get_ranking_config()
    overall_score = round(_calculate_overall_score(dimension_scores, config), 2)

    return {
        "summary": result.get("summary", ""),
        "dimension_scores": dimension_scores,
        "overall_score": overall_score,
        "rationale": rationale,
    }
