"""
📈 Monitor Summary

Comprehensive overview of entire system state.
Combines database status, rankings, events, discovery metrics.

Usage:
    python -m scripts.observability.monitor_summary

Output:
    - Database health summary
    - Top-ranked issues overview
    - Discovery activity summary
    - RAG system statistics
    - Recent events
"""

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
