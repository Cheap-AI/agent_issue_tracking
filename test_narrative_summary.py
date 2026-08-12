"""Quick test for narrative summary generation."""

from backend.workflows.discover_issue import discover_issue

# Test with a new topic
result = discover_issue(
    topic="climate change adaptation",
    target_issue_count=2,
    seed_created_issues=True
)

print("\n✅ Discovery complete!")
print(f"Created: {len(result.get('created_issues', []))} issues")
print(f"Report ID: {result['report']['report_id']}")
print("\nRun: .venv\\Scripts\\python.exe scripts\\view_discovery_reports.py")
print("to see the narrative summary!")
