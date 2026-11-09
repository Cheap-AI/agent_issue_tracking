"""Estimate when an issue's underlying problem began (its "origin").

One LLM call, grounded only in saved material (issue text, research, timeline, dated events).
The model's answer is validated and clamped by `validate_origin` before anything is stored, so
a bad or invented answer cannot violate the basic rules (see that function).
"""
from __future__ import annotations

import json
import logging
import re
from datetime import date
from pathlib import Path
from typing import Any

from backend.core.llm import bulk_model, get_bulk_client, load_prompt

logger = logging.getLogger(__name__)

PRECISIONS = ("year", "decade", "century", "era", "unknown")
CONFIDENCES = ("low", "medium", "high")
MIN_YEAR = -5000
BASIS_MAX_CHARS = 300

_PROMPT_PATH = Path(__file__).resolve().parents[1] / "prompts" / "origin" / "system_prompt.md"
_FALLBACK_PROMPT = (
    "Estimate when this issue's underlying problem began. Reply as JSON with origin_year, "
    "origin_precision (year|decade|century|era|unknown), origin_confidence (low|medium|high) and "
    "origin_basis. Answer unknown rather than guess."
)

UNKNOWN: dict[str, Any] = {
    "origin_year": None,
    "origin_precision": "unknown",
    "origin_confidence": "low",
    "origin_basis": "",
}


def earliest_event_year(events: list[dict[str, Any]] | None) -> int | None:
    """Year of the earliest dated event. Accepts DB events (event_date) and agent drafts (date)."""
    years: list[int] = []
    for event in events or []:
        raw = event.get("event_date") or event.get("date")
        match = re.match(r"^\s*(-?\d{1,4})", str(raw)) if raw else None
        if match:
            years.append(int(match.group(1)))
    return min(years) if years else None


def validate_origin(raw: dict[str, Any] | None, earliest_event: int | None = None) -> dict[str, Any]:
    """Turn a model answer into a storable origin dict, enforcing the rules.

    - bad/missing fields fall back to "unknown" (a valid answer);
    - the year is rounded down to its stated precision (decade -> 1940, century -> 1900);
    - an estimate later than the earliest dated event is impossible, so it is moved back to
      that event's year and confidence is capped at "medium".
    """
    raw = raw or {}
    precision = raw.get("origin_precision")
    confidence = raw.get("origin_confidence")
    basis = str(raw.get("origin_basis") or "").strip()[:BASIS_MAX_CHARS]

    try:
        year = int(raw.get("origin_year"))
    except (TypeError, ValueError):
        year = None
    if year is not None and not (MIN_YEAR <= year <= date.today().year):
        year = None

    if precision not in PRECISIONS or precision == "unknown" or year is None:
        return {**UNKNOWN, "origin_basis": basis}
    if confidence not in CONFIDENCES:
        confidence = "low"

    if precision == "decade":
        year = year // 10 * 10
    elif precision == "century":
        year = year // 100 * 100

    if earliest_event is not None and year > earliest_event:
        year = earliest_event
        if confidence == "high":
            confidence = "medium"
        basis = (basis + " (moved back to the earliest recorded event)").strip()[: BASIS_MAX_CHARS + 50]

    return {
        "origin_year": year,
        "origin_precision": precision,
        "origin_confidence": confidence,
        "origin_basis": basis,
    }


def _events_text(events: list[dict[str, Any]] | None, limit: int = 25) -> str:
    lines = []
    for e in (events or [])[:limit]:
        when = e.get("event_date") or e.get("date") or "undated"
        lines.append(f"- {when}: {e.get('title', '')} - {str(e.get('description', ''))[:150]}")
    return "\n".join(lines) or "No dated events saved."


def estimate_origin(
    title: str,
    summary: str = "",
    why: str = "",
    research: str = "",
    timeline: str = "",
    events: list[dict[str, Any]] | None = None,
) -> dict[str, Any] | None:
    """Estimate and validate an issue's origin.

    Never raises. Returns None if the LLM call failed (leave the columns NULL so it is retried later);
    a genuine "unknown" answer from the model is returned as a normal dict.
    """
    user_prompt = (
        f"Issue: {title}\n\nSummary:\n{summary[:1500]}\n\nWhy it matters:\n{why[:800]}\n\n"
        f"Research notes:\n{research[:3500]}\n\nTimeline notes:\n{timeline[:1500]}\n\n"
        f"Dated events:\n{_events_text(events)}"
    )
    try:
        client = get_bulk_client()
        response = client.chat.completions.create(
            model=bulk_model("OPENAI_ORIGIN_MODEL", "gpt-4o-mini"),
            messages=[
                {"role": "system", "content": load_prompt(_PROMPT_PATH, _FALLBACK_PROMPT)},
                {"role": "user", "content": user_prompt},
            ],
            temperature=0.2,
            max_tokens=400,
            response_format={"type": "json_object"},
        )
        raw = json.loads(response.choices[0].message.content)
    except Exception as e:  # never block issue creation on this
        logger.warning("Origin estimation failed for %r: %s", title, e)
        return None
    return validate_origin(raw, earliest_event_year(events))
