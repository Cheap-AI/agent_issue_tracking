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
