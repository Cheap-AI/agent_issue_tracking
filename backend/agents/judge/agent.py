"""LLM-as-judge: evaluates draft work from other agents before it proceeds.

Used as a quality gate inside the agentic LangGraph pipeline:
- judge_research: is the discover_research agent's draft dossier grounded and complete enough?
- judge_summary: is the summarize_rank agent's summary faithful to the research and are the
  dimension scores reasonable (not generic defaults)?

Both return a verdict dict: {"approved": bool, "score": int (0-10), "feedback": str}.
The feedback string is fed back into the producing agent on retry.
"""
from __future__ import annotations

import json
import os
from typing import Any

from langfuse.openai import OpenAI

client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
DEFAULT_MODEL = os.getenv("OPENAI_JUDGE_MODEL", "gpt-4o-mini")


_JUDGE_RESPONSE_SCHEMA = """Respond as JSON:
{
  "approved": <true|false>,
  "score": <0-10>,
  "feedback": "<1-3 sentences: what's missing or wrong, or why it's good>"
}"""


# Shared judge call: any rubric-specific system/user prompt in, a verdict dict out.
def _run_judge(system_prompt: str, user_prompt: str) -> dict[str, Any]:
    try:
        response = client.chat.completions.create(
            model=DEFAULT_MODEL,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            temperature=0.0,
            max_tokens=400,
            response_format={"type": "json_object"},
        )
        result = json.loads(response.choices[0].message.content)
        return {
            "approved": bool(result.get("approved", False)),
            "score": int(result.get("score", 0)),
            "feedback": str(result.get("feedback", "")),
        }
    except Exception as exc:
        # Fail closed: an unparsable/failed judge call should not silently approve bad work.
        return {"approved": False, "score": 0, "feedback": f"Judge call failed: {exc}"}


JUDGE_RESEARCH_SYSTEM_PROMPT = f"""You are a quality gate for a research dossier about a candidate issue.

Approve only if the dossier:
- Makes a specific, factual claim about why this issue matters (not vague generalities)
- Is grounded in the search results/events provided (not just restating the topic)
- Is sufficiently distinct from existing issues (no near-duplicate already covers it)

Reject if the dossier is thin, generic, unsupported by evidence, or likely a duplicate.

{_JUDGE_RESPONSE_SCHEMA}"""


JUDGE_SUMMARY_SYSTEM_PROMPT = f"""You are a quality gate for an executive summary and importance scores.

Approve only if:
- The summary is faithful to the research (no claims not supported by the research dossier)
- The summary is concise (2-4 paragraphs) and covers what/impact/status
- The dimension scores (severity/impact/scale/recency, 0-10) are differentiated and justified
  by the research, not generic defaults (e.g. all 5s)

Reject if the summary hallucinates beyond the research, or the scores don't match the narrative.

{_JUDGE_RESPONSE_SCHEMA}"""


def judge_research(candidate: dict[str, Any], research_content: str, events: list[dict[str, Any]]) -> dict[str, Any]:
    """Judge a discover_research draft (candidate + research dossier + events)."""
    user_prompt = f"""Candidate: {json.dumps(candidate, default=str)[:1000]}

Research dossier:
{research_content[:2000]}

Events found ({len(events)}):
{json.dumps(events, default=str)[:1000]}"""

    return _run_judge(JUDGE_RESEARCH_SYSTEM_PROMPT, user_prompt)


def judge_summary(
    candidate: dict[str, Any],
    research_content: str,
    summary: str,
    dimension_scores: dict[str, int],
) -> dict[str, Any]:
    """Judge a summarize_rank draft (summary + dimension scores) against the research."""
    user_prompt = f"""Candidate: {json.dumps(candidate, default=str)[:500]}

Research dossier:
{research_content[:2000]}

Summary:
{summary[:1500]}

Dimension scores: {json.dumps(dimension_scores)}"""

    return _run_judge(JUDGE_SUMMARY_SYSTEM_PROMPT, user_prompt)
