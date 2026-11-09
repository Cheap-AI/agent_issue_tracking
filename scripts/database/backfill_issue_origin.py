#!/usr/bin/env python3
"""
Estimate when each issue's underlying problem began and (optionally) store it.

DRY RUN BY DEFAULT: prints what it would write and changes nothing. The database is shared
and holds real data, so look at the estimates before using --apply.

Usage:
    python -m scripts.database.backfill_issue_origin --limit 5          # preview 5 issues
    python -m scripts.database.backfill_issue_origin --apply            # write all missing
    python -m scripts.database.backfill_issue_origin --apply --force    # also redo filled ones
    python -m scripts.database.backfill_issue_origin --issue iss-0003   # one issue

Evidence used: the issue text plus its saved research and timeline components and its dated
events. Raw search results are not stored, so they are not available.
"""
import argparse

from dotenv import load_dotenv

load_dotenv()

from backend.core.issue import list_events_for_issue, list_issues, set_issue_origin  # noqa: E402
from backend.core.knowledge import read_current  # noqa: E402
from backend.services.origin import estimate_origin  # noqa: E402


def _component(issue_id: str, name: str) -> str:
    current = read_current(issue_id, name)
    return current[1] if current else ""


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--apply", action="store_true", help="write results (default: preview only)")
    parser.add_argument("--force", action="store_true", help="re-estimate issues that already have an origin")
    parser.add_argument("--limit", type=int, default=0, help="stop after N issues (0 = all)")
    parser.add_argument("--issue", help="only this issue id")
    args = parser.parse_args()

    issues = list_issues()
    if args.issue:
        issues = [i for i in issues if i["id"] == args.issue]
    if not args.force:
        issues = [i for i in issues if i.get("origin_precision") is None]
    if args.limit:
        issues = issues[: args.limit]

    mode = "APPLY" if args.apply else "DRY RUN (nothing is written)"
    print(f"\n{mode}: {len(issues)} issue(s)\n")

    written = failed = 0
    for issue in issues:
        issue_id = issue["id"]
        origin = estimate_origin(
            issue["title"],
            issue["summary"],
            issue["why"],
            research=_component(issue_id, "research"),
            timeline=_component(issue_id, "timeline"),
            events=list_events_for_issue(issue_id),
        )
        if origin is None:
            failed += 1
            print(f"{issue_id}  {issue['title'][:60]}\n    FAILED (LLM error), left NULL\n")
            continue
        year = origin["origin_year"] if origin["origin_year"] is not None else "unknown"
        print(
            f"{issue_id}  {issue['title'][:60]}\n"
            f"    {year} ({origin['origin_precision']}, {origin['origin_confidence']} confidence)\n"
            f"    basis: {origin['origin_basis']}\n"
        )
        if args.apply:
            set_issue_origin(issue_id, **origin)
            written += 1

    print(f"Done. estimated={len(issues) - failed} failed={failed} written={written}")
    if not args.apply:
        print("Preview only. Re-run with --apply to write.")


if __name__ == "__main__":
    main()
