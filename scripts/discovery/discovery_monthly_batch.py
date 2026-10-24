#!/usr/bin/env python3
"""Run the discovery agent once per month over a date range, each run producing
~target_issue_count issues plus a versioned monthly report for that (year, month).

The discovery agent is instructed to tag target_year/target_month on each issue it
creates, but LLM compliance isn't guaranteed - this script force-corrects those
fields after each run (we already know which month we asked it to cover) so the
monthly report is always filed under the right (year, month) instead of falling
back to the current calendar month.

Usage:
    python -m scripts.discovery.discovery_monthly_batch --start 2026-01 --end 2026-06
"""
from __future__ import annotations

import argparse
import calendar
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from sqlalchemy import text

from backend.agents.discovery.agent import discover_issues
from backend.core.db import get_session
from backend.workflows.discover_issue import _build_memory_context
from backend.workflows.discovery_reports import generate_report, save_report
from backend.workflows.monthly_reports import generate_monthly_report, save_monthly_report


def _force_target_month(issue_ids: list[str], year: int, month: int) -> None:
    """Overwrite target_year/target_month for the given issues, regardless of what the agent set."""
    if not issue_ids:
        return
    with get_session() as session:
        session.execute(
            text("UPDATE issues SET target_year = :year, target_month = :month WHERE id = ANY(:ids)"),
            {"year": year, "month": month, "ids": issue_ids},
        )
        session.commit()


def run_month(year: int, month: int, target_issue_count: int, max_iterations: int) -> dict:
    month_name = calendar.month_name[month]
    topic = f"biggest issues and news in {month_name} {year}"
    instruction = (
        f"Find {target_issue_count} specific, distinct, evidence-backed issues that were prominent "
        f"news/events in {month_name} {year} specifically (not generic timeless issues). Search for "
        f"real news from that month. For every create_issue call, pass target_year={year} and "
        f"target_month={month}."
    )

    memory_context = _build_memory_context(topic, instruction)
    result = discover_issues(
        topic=topic,
        instruction=instruction,
        target_issue_count=target_issue_count,
        require_evaluation=True,
        max_results=10,
        max_iterations=max_iterations,
        seed_created_issues=True,
        require_human_review=False,
        override_human_review=False,
        memory_context=memory_context,
    )

    created_issues = result.get("created_issues", [])
    issue_ids = [issue["id"] for issue in created_issues]
    _force_target_month(issue_ids, year, month)
    for issue in created_issues:
        issue["target_year"] = year
        issue["target_month"] = month

    report = generate_report(result, topic, instruction)
    report_id = save_report(report)

    monthly = generate_monthly_report(year, month, created_issues)
    monthly_report_id = save_monthly_report(
        year, month, monthly["overview"], monthly["big_picture"], monthly["metadata"]
    )

    print(f"\n=== {month_name} {year} ===")
    print(f"Created {len(created_issues)} issues (report_id={report_id}, monthly_report_id={monthly_report_id})")
    for issue in created_issues:
        print(f"  - {issue['id']}: {issue['title']}")
    if result.get("proposed_duplicates"):
        print(f"Merged as duplicates: {len(result['proposed_duplicates'])}")

    return result


def _month_range(start: str, end: str) -> list[tuple[int, int]]:
    start_year, start_month = (int(p) for p in start.split("-"))
    end_year, end_month = (int(p) for p in end.split("-"))
    months = []
    y, m = start_year, start_month
    while (y, m) <= (end_year, end_month):
        months.append((y, m))
        m += 1
        if m > 12:
            m = 1
            y += 1
    return months


def main() -> None:
    parser = argparse.ArgumentParser(description="Run discovery once per month across a range")
    parser.add_argument("--start", required=True, help="Start month, YYYY-MM")
    parser.add_argument("--end", required=True, help="End month, YYYY-MM (inclusive)")
    parser.add_argument("--target-issue-count", type=int, default=6)
    parser.add_argument("--max-iterations", type=int, default=40)
    args = parser.parse_args()

    for year, month in _month_range(args.start, args.end):
        run_month(year, month, args.target_issue_count, args.max_iterations)


if __name__ == "__main__":
    main()
