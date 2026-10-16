"""
📝 Monitor Issues

Inspect detailed information about specific or all issues.
Shows: title, summary, tags, why, created date

Usage:
    python -m scripts.inspect_issues

    python -m scripts.inspect_issues --id iss-0001

    python -m scripts.inspect_issues --tag technology

Output:
    - Issue metadata (title, summary, tags)
    - Creation timestamps
    - Issue relationships
"""
from backend.core.issue import list_issues


def main() -> None:
    issues = list_issues()
    if not issues:
        print("No issues found.")
        return

    for issue in issues:
        print(f"ID: {issue['id']}")
        print(f"Title: {issue['title']}")
        print(f"Summary: {issue['summary']}")
        print("-" * 40)


if __name__ == "__main__":
    main()
