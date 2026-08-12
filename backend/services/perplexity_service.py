"""Perplexity AI search service integration.

Perplexity provides real-time, research-focused search with citations.
Use for: research queries, fact-checking, detailed analysis.
"""
import os
from typing import Any

import requests


PERPLEXITY_API_KEY = os.getenv("PERPLEXITY_API_KEY")
PERPLEXITY_API_URL = "https://api.perplexity.ai/chat/completions"


def is_configured() -> bool:
    """Check if Perplexity API key is configured."""
    # DISABLED: Perplexity API has connection issues, using Tavily only for now
    return False


def search(
    query: str,
    model: str = "sonar-pro",
    max_tokens: int = 1000
) -> list[dict[str, Any]]:
    """Search using Perplexity AI.
    
    Args:
        query: Search query
        model: Perplexity model to use (online models have web access)
        max_tokens: Max response length
        
    Returns:
        List of result dicts with keys: content, citations, title, url
        Format: [{"content": "...", "citations": ["url1", "url2"], "title": "...", "url": "..."}]
    """
    if not is_configured():
        raise RuntimeError("PERPLEXITY_API_KEY not configured. Add it to your .env file.")
    
    headers = {
        "Authorization": f"Bearer {PERPLEXITY_API_KEY}",
        "Content-Type": "application/json"
    }
    
    payload = {
        "model": model,
        "messages": [
            {
                "role": "system",
                "content": "You are a research assistant. Provide factual, well-cited information."
            },
            {
                "role": "user",
                "content": query
            }
        ],
        "max_tokens": max_tokens,
        "temperature": 0.2
    }
    
    try:
        response = requests.post(
            PERPLEXITY_API_URL,
            json=payload,
            headers=headers,
            timeout=30
        )
        response.raise_for_status()
        data = response.json()
        
        # Extract content and citations
        choice = data.get("choices", [{}])[0]
        message = choice.get("message", {})
        content = message.get("content", "")
        citations = data.get("citations", [])
        
        # Format as list of results (similar to Tavily structure)
        return [
            {
                "content": content,
                "citations": citations,
                "title": f"Perplexity Search: {query[:100]}",
                "url": citations[0] if citations else ""
            }
        ]
    except requests.exceptions.HTTPError as e:
        # Log the error response for debugging
        try:
            error_details = e.response.json()
        except:
            error_details = e.response.text
        print(f"[DEBUG] Perplexity HTTP Error: {e.response.status_code}")
        print(f"[DEBUG] Response: {error_details}")
        raise
    except Exception as e:
        print(f"[DEBUG] Perplexity Error: {str(e)}")
        raise
        
    except requests.exceptions.RequestException as e:
        raise RuntimeError(f"Perplexity API error: {e}")


def compare_search(query: str) -> dict[str, list]:
    """Run query through both Tavily and Perplexity for comparison.
    
    Returns:
        Dict with keys: tavily_results, perplexity_results
    """
    from backend.services import search_service
    
    results = {}
    
    if search_service.is_configured():
        try:
            results["tavily_results"] = search_service.search(query, max_results=5)
        except Exception as e:
            results["tavily_results"] = []
            results["tavily_error"] = str(e)
    else:
        results["tavily_results"] = []
    
    if is_configured():
        try:
            results["perplexity_results"] = search(query)
        except Exception as e:
            results["perplexity_results"] = []
            results["perplexity_error"] = str(e)
    else:
        results["perplexity_results"] = []
    
    return results
