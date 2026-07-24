import os

from tavily import TavilyClient

_tavily_api_key = os.getenv("TAVILY_API_KEY")
_client = TavilyClient(api_key=_tavily_api_key) if _tavily_api_key else None


def is_configured() -> bool:
    """Whether a Tavily API key is available."""
    return _client is not None


def search(topic: str, max_results: int = 5) -> list[dict[str, str]]:
    """Search Tavily for a topic and return the raw list of result dicts
    (each with title/url/content). Raises RuntimeError if not configured."""
    if _client is None:
        raise RuntimeError("Tavily API key not configured. Please add TAVILY_API_KEY to your .env file.")

    search_result = _client.search(query=topic, search_depth="basic", max_results=max_results)
    return search_result.get("results", [])
