"""Quick database status check."""
from backend.core.db import get_session
from sqlalchemy import text

with get_session() as session:
    # Check reports
    reports = session.execute(text(
        'SELECT id, topic, actual_created, created_at FROM discovery_reports ORDER BY created_at DESC LIMIT 5'
    )).fetchall()
    
    print(f"📊 Reports in DB: {len(reports)}")
    for r in reports:
        print(f"  Report {r[0]}: '{r[1]}' - {r[2]} issues - {str(r[3])[:19]}")
    
    # Check issues
    print()
    issues = session.execute(text(
        "SELECT id, title FROM issues ORDER BY created_at DESC LIMIT 5"
    )).fetchall()
    
    print(f"📝 Recent issues: {len(issues)}")
    for i in issues:
        print(f"  {i[0]}: {i[1][:70]}")
    
    # Check embeddings
    print()
    embeddings = session.execute(text("SELECT COUNT(*) FROM issue_embeddings")).scalar()
    chunks = session.execute(text("SELECT COUNT(*) FROM discovery_report_chunks")).scalar()
    
    print(f"🔍 RAG System:")
    print(f"  Issue embeddings: {embeddings}")
    print(f"  Report chunks: {chunks}")
    
    # Check events
    print()
    events = session.execute(text("SELECT COUNT(*) FROM events")).scalar()
    print(f"📅 Events collected: {events}")
