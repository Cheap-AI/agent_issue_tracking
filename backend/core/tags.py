"""Tag spaces for issues.

Every tag lives in exactly one space:
- geography:       where the issue plays out (countries, regions, "global")
- topics:          what kind of issue it is (health, economy, policy, ...)
- affected_groups: who is hit by it (parents, students, seniors, ...)

The flat ``Issue.tags`` column is kept as the union of the three, so older readers
(reports, chat) keep working.
"""
from __future__ import annotations

import re
from collections import Counter
from typing import Iterable

SPACES = ("geography", "topics", "affected_groups")

# Used only to sort legacy flat tags into spaces (migration backfill and API callers that
# still send `tags`). New agent output names the space explicitly.
LEGACY_GEOGRAPHY = frozenset(
    {
        "global", "africa", "asia", "europe", "latin-america", "middle-east",
        "north-america", "south-america", "oceania", "caribbean",
        "afghanistan", "canada", "north-korea", "u.s.", "u.k.", "us", "uk", "usa",
        "china", "russia", "india", "japan", "korea", "south-korea", "ukraine",
        "israel", "iran", "mexico", "brazil", "australia", "germany", "france",
    }
)


def tag_key(value: str) -> str:
    """Comparison key: case-insensitive, spaces and hyphens equivalent."""
    return re.sub(r"[\s_]+", "-", value.strip().lower())


def canonicalize(values: Iterable[str] | None, existing: Iterable[str] = ()) -> list[str]:
    """Clean a list of tags for one space.

    Reuses the spelling of an existing value when it matches ignoring case/spaces
    (so "middle east" becomes "Middle-East" if that is already in use), drops blanks,
    and removes duplicates while keeping order.
    """
    known = {tag_key(v): v for v in existing if isinstance(v, str) and v.strip()}
    out: list[str] = []
    seen: set[str] = set()
    for raw in values or []:
        if not isinstance(raw, str) or not raw.strip():
            continue
        key = tag_key(raw)
        if key in seen:
            continue
        seen.add(key)
        out.append(known.get(key, key if " " in raw.strip() else raw.strip()))
    return out


def split_legacy_tags(tags: Iterable[str] | None) -> dict[str, list[str]]:
    """Sort a flat tag list into spaces. Anything that is not a known place is a topic."""
    result: dict[str, list[str]] = {space: [] for space in SPACES}
    for tag in tags or []:
        if not isinstance(tag, str) or not tag.strip():
            continue
        space = "geography" if tag_key(tag) in LEGACY_GEOGRAPHY else "topics"
        result[space].append(tag.strip())
    return result


def union_tags(geography: Iterable[str], topics: Iterable[str], affected_groups: Iterable[str]) -> list[str]:
    """Flat, de-duplicated list for the legacy ``tags`` column."""
    seen: set[str] = set()
    out: list[str] = []
    for tag in [*geography, *topics, *affected_groups]:
        key = tag_key(tag)
        if key not in seen:
            seen.add(key)
            out.append(tag)
    return out


def vocabulary_from_rows(rows: Iterable[dict[str, Iterable[str] | None]]) -> dict[str, list[dict[str, int | str]]]:
    """Count values per space, most used first. ``rows`` are dicts keyed by space name."""
    counters = {space: Counter() for space in SPACES}
    for row in rows:
        for space in SPACES:
            counters[space].update(v for v in (row.get(space) or []) if isinstance(v, str))
    return {
        space: [
            {"value": value, "count": count}
            for value, count in sorted(counters[space].items(), key=lambda kv: (-kv[1], kv[0].lower()))
        ]
        for space in SPACES
    }
