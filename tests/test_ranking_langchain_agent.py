"""Tests for the LangChain comparison variant of the ranking agent.

The LLM call is mocked (no real OpenAI/network calls); persistence runs against the real test
database, matching the convention in tests/test_issue_storage.py.
"""
import unittest
from unittest.mock import MagicMock, patch

from backend.agents.ranking import agent_langchain
from backend.agents.ranking.agent_langchain import DimensionScores
from backend.core.issue import create_issue
from backend.core.knowledge import update_component


class RankingLangchainAgentTests(unittest.TestCase):
    def test_score_issue_langchain_returns_expected_shape(self) -> None:
        issue = create_issue("Test issue", "A test summary.")
        update_component(issue["id"], "research", "Some research content.")

        fake_scores = DimensionScores(
            severity=8, severity_reason="r",
            impact=7, impact_reason="r",
            scale=6, scale_reason="r",
            recency=9, recency_reason="r",
        )
        with patch.object(agent_langchain, "_llm", MagicMock(invoke=MagicMock(return_value=fake_scores))):
            result = agent_langchain.score_issue_langchain(issue["id"])

        self.assertEqual(result["issue_id"], issue["id"])
        self.assertEqual(result["dimension_scores"], {"severity": 8, "impact": 7, "scale": 6, "recency": 9})
        self.assertEqual(result["overall_score"], 7.5)
        self.assertEqual(result["rank"], 1)

    def test_unknown_issue_raises(self) -> None:
        with self.assertRaises(ValueError):
            agent_langchain.score_issue_langchain("iss-9999")

    def test_llm_failure_falls_back_to_neutral_scores(self) -> None:
        issue = create_issue("Fallback issue", "A test summary.")
        update_component(issue["id"], "research", "Some research content.")

        with patch.object(agent_langchain, "_llm", MagicMock(invoke=MagicMock(side_effect=RuntimeError("boom")))):
            result = agent_langchain.score_issue_langchain(issue["id"])

        self.assertEqual(result["dimension_scores"], {"severity": 5, "impact": 5, "scale": 5, "recency": 5})


if __name__ == "__main__":
    unittest.main()
