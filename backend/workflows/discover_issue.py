"""Discover a new issue from a search topic: search Tavily, create an issue folder,
and save the raw results as the first immutable research version.

Usage: python -m backend.workflows.discover_issue "<topic>"
"""
import sys
from typing import Any

from backend.core import knowledge
from backend.core.issue import create_issue
from backend.services import search_service


def discover_issue(topic: str, max_results: int = 5) -> dict[str, Any]:
    topic = topic.strip()
    if not topic:
        raise ValueError("Topic is required")

    results = search_service.search(topic, max_results=max_results)

    summary = f"Initial findings for '{topic}':\n\n"
    for res in results[:3]:
        summary += f"- {res.get('content', '')[:200]}...\n"

    issue = create_issue(title=topic, summary=summary)

    research_content = "\n\n".join(
        f"## {res.get('title', '')}\n{res.get('url', '')}\n\n{res.get('content', '')}"
        for res in results
    )
    knowledge.update_component(issue["id"], "research", research_content)

    return issue


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print('Usage: python -m backend.workflows.discover_issue "<topic>"')
        sys.exit(1)

    created = discover_issue(" ".join(sys.argv[1:]))
    print(f"Created issue {created['id']}: {created['title']}")
