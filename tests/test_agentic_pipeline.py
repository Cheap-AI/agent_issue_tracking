"""Tests for the agentic LangGraph pipeline: judge loop, human-in-the-loop, persistence.

All agent/judge calls are mocked (no real OpenAI/Tavily calls). Persistence runs against the
real test Postgres database (see tests/conftest.py), matching the repo's existing convention.
"""
import unittest
from unittest.mock import patch
from uuid import uuid4

from backend.core.issue import get_issue
from backend.workflows import langgraph_agentic_pipeline as pipeline

CANDIDATE = {
    "decision": "create",
    "title": "Test Outage",
    "summary": "A short candidate summary.",
    "why": "Affects many users.",
    "tags": ["test"],
    "research_dossier": "Detailed research findings.",
}

RESEARCH_RESULT = {
    "candidate": CANDIDATE,
    "research_content": CANDIDATE["research_dossier"],
    "events": [{"date": "2026-01-01", "title": "Incident", "description": "...", "source": "https://x"}],
}

SUMMARY_RESULT = {
    "summary": "Executive summary text.",
    "dimension_scores": {"severity": 8, "impact": 7, "scale": 6, "recency": 9},
    "overall_score": 7.5,
    "rationale": {},
}

APPROVED = {"approved": True, "score": 9, "feedback": "Solid."}
REJECTED = {"approved": False, "score": 2, "feedback": "Too thin."}


class AgenticPipelineTests(unittest.TestCase):
    def _patches(self, judge_research_verdicts, judge_summary_verdicts):
        return (
            patch.object(pipeline, "discover_and_research", return_value=RESEARCH_RESULT),
            patch.object(pipeline, "judge_research", side_effect=judge_research_verdicts),
            patch.object(pipeline, "summarize_and_rank", return_value=SUMMARY_RESULT),
            patch.object(pipeline, "judge_summary", side_effect=judge_summary_verdicts),
        )

    def test_approved_pipeline_persists_after_human_approval(self) -> None:
        thread_id = str(uuid4())
        patches = self._patches([APPROVED], [APPROVED])
        with patches[0], patches[1], patches[2], patches[3]:
            started = pipeline.start_pipeline(thread_id, topic="outages")

        self.assertEqual(started["status"], "pending_review")
        self.assertEqual(started["pending_review"]["candidate"]["title"], "Test Outage")

        resumed = pipeline.resume_pipeline(thread_id, decision="approve")

        self.assertEqual(resumed["status"], "persisted")
        issue = get_issue(resumed["persisted_issue_id"])
        self.assertEqual(issue["title"], "Test Outage")

    def test_human_rejection_does_not_persist(self) -> None:
        thread_id = str(uuid4())
        patches = self._patches([APPROVED], [APPROVED])
        with patches[0], patches[1], patches[2], patches[3]:
            pipeline.start_pipeline(thread_id, topic="outages")
            resumed = pipeline.resume_pipeline(thread_id, decision="reject")

        self.assertEqual(resumed["status"], "rejected")
        self.assertIsNone(resumed["persisted_issue_id"])

    def test_summary_judge_loop_exhausts_retries_and_rejects(self) -> None:
        thread_id = str(uuid4())
        # Research approved immediately; summary judge rejects every attempt (1 initial + 2 retries).
        patches = self._patches([APPROVED], [REJECTED, REJECTED, REJECTED])
        with patches[0], patches[1], patches[2], patches[3]:
            result = pipeline.start_pipeline(thread_id, topic="outages")

        self.assertEqual(result["status"], "rejected")
        self.assertIsNone(result["pending_review"])


if __name__ == "__main__":
    unittest.main()
