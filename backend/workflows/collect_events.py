"""Events collection workflow: Extract and store timestamped events for an issue."""
import json
import os
from datetime import datetime
from typing import Any

from openai import OpenAI

from backend.core.db import get_session
from backend.models.db_models import Event
from backend.services import search_service
from backend.core.issue import get_issue


client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
DEFAULT_MODEL = os.getenv("OPENAI_EVENTS_MODEL", "gpt-4o-mini")

SYSTEM_PROMPT = """You are an events researcher for an Issue Intelligence Platform.

Extract timestamped events from search results. Return valid JSON array:
[
  {
    "date": "2026-01-15",
    "title": "Event title",
    "description": "What happened and why it matters",
    "source": "https://..."
  }
]

Use null for date if unknown. Only return JSON, no extra text."""


def collect_events_for_issue(issue_id: str, search_query: str | None = None, max_results: int = 10) -> dict[str, Any]:
    """Research and collect events for an issue.
    
    Args:
        issue_id: Issue ID to collect events for
        search_query: Custom search query (uses issue title if not provided)
        max_results: Max Tavily search results
        
    Returns:
        Dict with keys: events_created, events, search_results_count, status
    """
    # Get issue details
    issue = get_issue(issue_id)
    if issue is None:
        return {"status": "error", "events_created": 0, "events": [], "error": "Issue not found"}
    
    if not search_query:
        search_query = f"{issue['title']} events announcements incidents"
    
    if not search_service.is_configured():
        return {"status": "error", "events_created": 0, "events": [], "error": "Tavily API not configured"}
    
    # Search for events
    try:
        web_results = search_service.search(search_query, max_results=max_results)
    except Exception as e:
        return {"status": "error", "events_created": 0, "events": [], "error": f"Search failed: {e}"}
    
    if not web_results:
        return {"status": "success", "events_created": 0, "events": [], "search_results_count": 0, "message": "No results found"}
    
    # Extract events using GPT
    context = "\n\n".join([
        f"Source: {r.get('url')}\nTitle: {r.get('title')}\nContent: {r.get('content', '')[:500]}"
        for r in web_results
    ])
    
    user_prompt = f"""Issue: {issue['title']}
Summary: {issue['summary']}

Search Results:
{context}

Extract timestamped events from the search results."""

    try:
        response = client.chat.completions.create(
            model=DEFAULT_MODEL,
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": user_prompt}
            ],
            temperature=0.5,
            max_tokens=2000
        )
        
        response_text = response.choices[0].message.content.strip()
        events_data = json.loads(response_text)
        
    except json.JSONDecodeError as e:
        return {"status": "error", "events_created": 0, "events": [], "error": f"Failed to parse response: {e}"}
    except Exception as e:
        return {"status": "error", "events_created": 0, "events": [], "error": f"GPT call failed: {e}"}
    
    # Save to database
    events_created = _save_events_to_db(issue_id, events_data)
    
    return {
        "status": "success",
        "events_created": events_created,
        "events": events_data,
        "search_results_count": len(web_results)
    }


def _save_events_to_db(issue_id: str, events_data: list[dict]) -> int:
    """Save extracted events to the database."""
    with get_session() as session:
        count = 0
        for event_dict in events_data:
            try:
                event = Event(
                    issue_id=issue_id,
                    event_date=event_dict.get("date"),
                    title=event_dict.get("title", ""),
                    description=event_dict.get("description", ""),
                    source_urls=[event_dict.get("source")] if event_dict.get("source") else [],
                    component_id=None
                )
                session.add(event)
                count += 1
            except Exception as e:
                print(f"Error creating event: {e}")
                continue
        
        session.commit()
        return count
