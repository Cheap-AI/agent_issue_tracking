"""View full summary from latest report."""

from backend.workflows.discovery_reports import load_recent_reports

reports = load_recent_reports(limit=1)
if reports:
    report = reports[0]
    print("=" * 70)
    print(f"Report: {report['metadata']['topic']}")
    print(f"Created: {report['metadata']['actual_created']} issues")
    print("=" * 70)
    print("\n" + report['summary'])
else:
    print("No reports found")
