"""Events Agent: Research and extract timestamped events for an issue.

This agent:
1. Searches for events using Tavily (web search)
2. Extracts event dates, titles, descriptions, and sources using GPT
3. Returns structured events with timestamps
4. Stores events in the database linked to the issue
"""
import json
import os
from typing import Any

from openai import OpenAI

from backend.services import search_service
from backend.services import perplexity_service
from backend.core.db import get_session
from backend.models.db_models import Event
from backend.core.issue import get_issue


client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
DEFAULT_MODEL = os.getenv("OPENAI_EVENTS_MODEL", "gpt-4o-mini")


SYSTEM_PROMPT = """You are an events researcher for an Issue Intelligence Platform.

Your role is to find and extract timestamped events related to a given issue.

When analyzing search results about an issue, you should:
1. Identify specific events (announcements, incidents, milestones, reports)
2. Extract the event date (YYYY-MM-DD format if available, or null if unknown)
3. Provide a clear title and description of what happened
4. Note the source URL
5. Be factual and specific

Return a JSON array of events:
[
  {
    "date": "2026-01-15",
    "title": "Event title",
    "description": "What happened and why it matters",
    "source": "https://..."
  }
]

If no date is found, use null for the date field.
Only return valid JSON array, no extra text."""


def collect_events_for_issue(
    issue_id: str,
    search_query: str | None = None,
    max_results: int = 10,
    use_perplexity: bool = False
) -> dict[str, Any]:
    """Research and collect events for an issue.
    
    Args:
        issue_id: Issue ID to collect events for
        search_query: Custom search query (uses issue title if not provided)
        max_results: Max search results (default 10)
        use_perplexity: Use Perplexity for research-focused search (default False = Tavily)
        
    Returns:
        Dict with keys: status, events_created, events, search_results_count, error (if any)
    """
    # Get issue details
    issue = get_issue(issue_id)
    if issue is None:
        return {
            "status": "error",
            "events_created": 0,
            "events": [],
            "error": "Issue not found"
        }
    
    if not search_query:
        search_query = f"{issue['title']} events announcements incidents"
    
    # Choose search service
    if use_perplexity:
        if not perplexity_service.is_configured():
            return {
                "status": "error",
                "events_created": 0,
                "events": [],
                "error": "Perplexity API not configured. Add PERPLEXITY_API_KEY to .env"
            }
        search_fn = lambda q: perplexity_service.search(q)
        service_name = "Perplexity"
    else:
        if not search_service.is_configured():
            return {
                "status": "error",
                "events_created": 0,
                "events": [],
                "error": "Tavily API not configured"
            }
        search_fn = lambda q: search_service.search(q, max_results=max_results)
        service_name = "Tavily"
    
    # Step 1: Search for events
    try:
        web_results = search_fn(search_query)
    except Exception as e:
        return {
            "status": "error",
            "events_created": 0,
            "events": [],
            "error": f"{service_name} search failed: {e}",
            "search_results_count": 0
        }
    
    if not web_results:
        return {
            "status": "success",
            "events_created": 0,
            "events": [],
            "search_results_count": 0,
            "message": "No search results found"
        }
    
    # Step 2: Use GPT to extract structured events from search results
    context = "\n\n".join([
        f"Source: {r.get('url')}\nTitle: {r.get('title')}\nContent: {r.get('content', '')[:500]}"
        for r in web_results
    ])
    
    user_prompt = f"""Issue: {issue['title']}
Summary: {issue['summary']}

Search Results:
{context}

Extract timestamped events from the search results above."""

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
        return {
            "status": "error",
            "events_created": 0,
            "events": [],
            "error": f"Failed to parse GPT response as JSON: {e}",
            "search_results_count": len(web_results)
        }
    except Exception as e:
        return {
            "status": "error",
            "events_created": 0,
            "events": [],
            "error": f"GPT call failed: {e}",
            "search_results_count": len(web_results)
        }
    
    # Step 3: Save events to database
    events_created = _save_events_to_db(issue_id, events_data)
    
    return {
        "status": "success",
        "events_created": events_created,
        "events": events_data,
        "search_results_count": len(web_results)
    }


def research_issue(
    issue_id: str,
    search_query: str,
    max_web_results: int = 5,
    max_rag_results: int = 3
) -> dict:
    """Research an issue by collecting timestamped events.
    
    This agent now focuses on finding events and evidence related to an issue.
    This updated version calls collect_events_for_issue instead of doing RAG+synthesis.
    
    Args:
        issue_id: Issue to research
        search_query: Query for web search
        max_web_results: Max Tavily search results (default 5) - unused, kept for compatibility
        max_rag_results: Max similar research chunks from RAG (default 3) - unused, kept for compatibility
        
    Returns:
        Dict with keys: status, events_created, version, research_content
    """
    # Call the events collection workflow
    result = collect_events_for_issue(
        issue_id=issue_id,
        search_query=search_query,
        max_results=max_web_results
    )
    
    # Transform the result to match the expected format for update_issue workflow
    return {
        "version": "events",  # Placeholder version
        "research_content": f"Collected {result.get('events_created', 0)} events from research",
        "events_extracted": result.get('events_created', 0),
        "sources": result.get('events', []),
        "status": result.get('status'),
        "message": result.get('message', 'Events collected successfully')
    }


def _save_events_to_db(issue_id: str, events_data: list[dict]) -> int:
    """Save extracted events to the database.
    
    Args:
        issue_id: Issue ID to associate with events
        events_data: List of event dicts with keys: date, title, description, source
        
    Returns:
        Number of events successfully created
    """
    with get_session() as session:
        count = 0
        for event_dict in events_data:
            try:
                event = Event(
                    issue_id=issue_id,
                    event_date=event_dict.get("date"),  # Can be null
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
