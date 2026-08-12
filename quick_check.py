from backend.core.db import get_session
from backend.models.db_models import DiscoveryReport, Issue

with get_session() as s:
    reports = s.query(DiscoveryReport).count()
    issues = s.query(Issue).count()
    last_report = s.query(DiscoveryReport).order_by(DiscoveryReport.id.desc()).first()
    
    print(f"Total reports: {reports}")
    print(f"Total issues: {issues}")
    if last_report:
        print(f"Last report ID: {last_report.id}")
        print(f"Last report topic: '{last_report.topic}'")
        print(f"Last report created: {last_report.created_at}")
        print(f"Last report actual_created: {last_report.actual_created}")
        print(f"Last report findings count: {len(last_report.findings if last_report.findings else [])}")
