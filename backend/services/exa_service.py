"""Exa AI search service integration.

Exa is a neural web search API that can return page text with each result.
Use for: research queries, finding recent sources, fact-checking.
"""
import os
from typing import Any

import requests

EXA_API_URL = "https://api.exa.ai/search"


def is_configured() -> bool:
    """Check if the Exa API key is configured."""
    return bool(os.getenv("EXA_API_KEY"))


def search(query: str, max_results: int = 5) -> list[dict[str, Any]]:
    """Search using Exa and return results in the same shape as the Tavily service.

    Follows Exa's recommended request: `type: auto` plus bare `contents.highlights` (token-efficient
    excerpts). `max_results` is an intentional cap to keep agent prompts small (Exa's default is 10).

    Returns:
        [{"title": "...", "url": "...", "content": "...", "published_date": "..."}]
    """
    if not is_configured():
        raise RuntimeError("EXA_API_KEY not configured. Add it to your .env file.")

    response = requests.post(
        EXA_API_URL,
        headers={"x-api-key": os.environ["EXA_API_KEY"], "Content-Type": "application/json"},
        json={
            "query": query,
            "type": "auto",
            "numResults": max_results,
            "contents": {"highlights": True},
        },
        timeout=30,
    )
    response.raise_for_status()

    return [
        {
            "title": item.get("title") or "",
            "url": item.get("url") or "",
            "content": "\n".join(item.get("highlights") or []),
            "published_date": item.get("publishedDate"),
        }
        for item in response.json().get("results", [])
    ]
