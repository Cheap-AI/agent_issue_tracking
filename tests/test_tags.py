"""Pure-logic tests for tag spaces (no database)."""
import json
from unittest.mock import patch

import pytest

from backend.core.tags import canonicalize, split_legacy_tags, union_tags, vocabulary_from_rows


pytestmark = pytest.mark.no_db


def test_split_legacy_tags_sorts_places_and_topics():
    out = split_legacy_tags(["Africa", "health", "U.S.", "policy", "global"])
    assert out["geography"] == ["Africa", "U.S.", "global"]
    assert out["topics"] == ["health", "policy"]
    assert out["affected_groups"] == []


def test_canonicalize_reuses_existing_spelling_and_dedupes():
    existing = ["Middle-East", "seniors"]
    assert canonicalize(["middle east", "Middle-East", "  "], existing) == ["Middle-East"]
    assert canonicalize(["SENIORS", "parents"], existing) == ["seniors", "parents"]
    assert canonicalize(None) == []


def test_canonicalize_new_multiword_value_is_hyphenated():
    assert canonicalize(["small business owners"]) == ["small-business-owners"]


def test_union_tags_dedupes_across_spaces():
    assert union_tags(["Asia"], ["health", "asia"], ["parents"]) == ["Asia", "health", "parents"]


def test_vocabulary_counts_most_used_first_and_empty_group_is_ok():
    vocab = vocabulary_from_rows(
        [
            {"geography": ["Africa"], "topics": ["health", "policy"], "affected_groups": []},
            {"geography": ["Africa", "Asia"], "topics": ["health"], "affected_groups": None},
        ]
    )
    assert vocab["geography"][0] == {"value": "Africa", "count": 2}
    assert vocab["topics"][0] == {"value": "health", "count": 2}
    assert vocab["affected_groups"] == []


def test_agents_expose_vocabulary_tool_and_three_tag_fields():
    from backend.agents.discover_research import agent as research
    from backend.agents.discovery import agent as discovery

    fake = {"geography": [], "topics": [], "affected_groups": []}
    for module, create_tool in ((discovery, "create_issue"), (research, "draft_create_issue")):
        tools = {t["function"]["name"]: t["function"] for t in module.TOOLS}
        assert "get_tag_vocabulary" in tools
        props = tools[create_tool]["parameters"]["properties"]
        assert {"geography", "topics", "affected_groups"} <= set(props)
        assert "tags" not in props
        json.dumps(module.TOOLS)
        with patch.object(module, "get_tag_vocabulary", return_value=fake):
            assert module._dispatch_tool("get_tag_vocabulary", {}) == fake


def test_draft_candidate_carries_the_three_spaces():
    from backend.agents.discover_research import agent as research

    out = research._dispatch_tool(
        "draft_create_issue",
        {"title": "t", "summary": "s", "why": "w", "geography": ["Asia"], "topics": ["health"],
         "affected_groups": ["seniors"], "research_dossier": "d"},
    )
    cand = out["candidate"]
    assert (cand["geography"], cand["topics"], cand["affected_groups"]) == (["Asia"], ["health"], ["seniors"])
