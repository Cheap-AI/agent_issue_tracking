from backend.core.db import get_session
from backend.models.db_models import DiscoveryReport

with get_session() as s:
    # Get last 3 reports
    reports = s.query(DiscoveryReport).order_by(DiscoveryReport.id.desc()).limit(3).all()
    
    for r in reports:
        print(f"\n{'='*70}")
        print(f"Report ID: {r.id}")
        print(f"Topic: '{r.topic}'")
        print(f"Created: {r.created_at}")
        print(f"Iterations: {r.iterations}")
        print(f"Target: {r.target_count}, Actual: {r.actual_created}")
        print(f"Findings: {len(r.findings if r.findings else [])}")
        print(f"API Usage: {r.api_usage}")
        print(f"\nSummary (first 500 chars):")
        print(r.summary[:500] if r.summary else "(empty)")
        if r.findings:
            print(f"\nFirst finding:")
            print(r.findings[0])
