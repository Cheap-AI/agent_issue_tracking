#!/usr/bin/env python3
"""Delete issues and show what will be cleaned up (CASCADE deletes)."""

import sys
from sqlalchemy import text
from backend.core.db import get_session


def show_issue_details(issue_id: str) -> dict:
    """Show what will be deleted for an issue."""
    with get_session() as session:
        # Get issue details
        issue = session.execute(
            text("SELECT id, title FROM issues WHERE id = :id"),
            {"id": issue_id}
        ).fetchone()
        
        if not issue:
            return None
        
        # Count related records
        component_count = session.execute(
            text("SELECT COUNT(*) FROM components WHERE issue_id = :id"),
            {"id": issue_id}
        ).scalar()
        
        event_count = session.execute(
            text("SELECT COUNT(*) FROM events WHERE issue_id = :id"),
            {"id": issue_id}
        ).scalar()
        
        embedding_count = session.execute(
            text("SELECT COUNT(*) FROM issue_embeddings WHERE issue_id = :id"),
            {"id": issue_id}
        ).scalar()
        
        tracked = session.execute(
            text("SELECT COUNT(*) FROM tracked_issues WHERE issue_id = :id"),
            {"id": issue_id}
        ).scalar()
        
        return {
            "id": issue[0],
            "title": issue[1],
            "components": component_count,
            "events": event_count,
            "embeddings": embedding_count,
            "tracked": tracked > 0
        }


def delete_issue(issue_id: str, dry_run: bool = True) -> bool:
    """Delete an issue and all related data (CASCADE)."""
    details = show_issue_details(issue_id)
    
    if not details:
        print(f"❌ Issue {issue_id} not found")
        return False
    
    print(f"\n{'[DRY RUN] ' if dry_run else ''}Deleting issue: {details['id']}")
    print(f"  Title: {details['title']}")
    print(f"  Will CASCADE delete:")
    print(f"    • {details['components']} components (research/summary/timeline/sources/questions)")
    print(f"    • {details['events']} events")
    print(f"    • {details['embeddings']} embeddings")
    print(f"    • {'1 tracked_issues row' if details['tracked'] else 'no tracked_issues'}")
    
    if dry_run:
        print(f"\n✓ Dry run complete. To actually delete, run: delete_issue('{issue_id}', dry_run=False)")
        return True
    
    with get_session() as session:
        session.execute(
            text("DELETE FROM issues WHERE id = :id"),
            {"id": issue_id}
        )
        session.commit()
    
    print(f"\n✅ Issue {issue_id} and all related data deleted")
    return True


def delete_all_issues(dry_run: bool = True) -> None:
    """Delete ALL issues and related data. Use with caution!"""
    with get_session() as session:
        counts = {
            "issues": session.execute(text("SELECT COUNT(*) FROM issues")).scalar(),
            "components": session.execute(text("SELECT COUNT(*) FROM components")).scalar(),
            "events": session.execute(text("SELECT COUNT(*) FROM events")).scalar(),
            "embeddings": session.execute(text("SELECT COUNT(*) FROM issue_embeddings")).scalar(),
            "tracked": session.execute(text("SELECT COUNT(*) FROM tracked_issues")).scalar(),
        }
    
    print(f"\n{'[DRY RUN] ' if dry_run else ''}Deleting ALL issues:")
    print(f"  {counts['issues']} issues")
    print(f"  Will CASCADE delete:")
    print(f"    • {counts['components']} components")
    print(f"    • {counts['events']} events")
    print(f"    • {counts['embeddings']} issue_embeddings")
    print(f"    • {counts['tracked']} tracked_issues")
    
    if dry_run:
        print(f"\n✓ Dry run complete. To actually delete ALL, run: delete_all_issues(dry_run=False)")
        return
    
    with get_session() as session:
        session.execute(text("DELETE FROM issues"))
        session.commit()
    
    print(f"\n✅ All issues and related data deleted")


def list_issues() -> None:
    """List all issues with their IDs."""
    with get_session() as session:
        issues = session.execute(
            text("""
                SELECT i.id, i.title, i.created_at,
                       COUNT(DISTINCT c.id) as components,
                       COUNT(DISTINCT e.id) as events
                FROM issues i
                LEFT JOIN components c ON c.issue_id = i.id
                LEFT JOIN events e ON e.issue_id = i.id
                GROUP BY i.id, i.title, i.created_at
                ORDER BY i.created_at DESC
            """)
        ).fetchall()
    
    if not issues:
        print("No issues found")
        return
    
    print(f"\nFound {len(issues)} issues:")
    print(f"{'ID':<12} {'Components':<12} {'Events':<10} {'Title':<50}")
    print("-" * 90)
    for issue in issues:
        title = issue[1][:47] + "..." if len(issue[1]) > 50 else issue[1]
        print(f"{issue[0]:<12} {issue[3]:<12} {issue[4]:<10} {title:<50}")


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage:")
        print("  python delete_issues.py list                    # List all issues")
        print("  python delete_issues.py show <issue-id>         # Show what will be deleted")
        print("  python delete_issues.py delete <issue-id>       # Delete one issue (dry-run)")
        print("  python delete_issues.py delete <issue-id> --yes # Actually delete one issue")
        print("  python delete_issues.py delete-all              # Delete all issues (dry-run)")
        print("  python delete_issues.py delete-all --yes        # Actually delete all issues")
        sys.exit(1)
    
    command = sys.argv[1]
    
    if command == "list":
        list_issues()
    
    elif command == "show":
        if len(sys.argv) < 3:
            print("Error: provide issue ID")
            sys.exit(1)
        details = show_issue_details(sys.argv[2])
        if details:
            print(f"\nIssue: {details['id']}")
            print(f"  Title: {details['title']}")
            print(f"  Components: {details['components']}")
            print(f"  Events: {details['events']}")
            print(f"  Embeddings: {details['embeddings']}")
            print(f"  Tracked: {'Yes' if details['tracked'] else 'No'}")
    
    elif command == "delete":
        if len(sys.argv) < 3:
            print("Error: provide issue ID")
            sys.exit(1)
        issue_id = sys.argv[2]
        dry_run = "--yes" not in sys.argv
        delete_issue(issue_id, dry_run=dry_run)
    
    elif command == "delete-all":
        dry_run = "--yes" not in sys.argv
        if not dry_run:
            print("⚠️  WARNING: This will delete ALL issues and related data!")
            confirm = input("Type 'DELETE ALL' to confirm: ")
            if confirm != "DELETE ALL":
                print("Cancelled")
                sys.exit(0)
        delete_all_issues(dry_run=dry_run)
    
    else:
        print(f"Unknown command: {command}")
        sys.exit(1)
