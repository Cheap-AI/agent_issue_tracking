"""Quick script to verify Phase 2 schema changes."""
from backend.core.db import get_session
from sqlalchemy import text

with get_session() as session:
    # List all tables in public schema
    result = session.execute(
        text("SELECT table_name FROM information_schema.tables WHERE table_schema='public' ORDER BY table_name")
    )
    tables = [row[0] for row in result.fetchall()]
    
    print("Tables in database:")
    for table in tables:
        print(f"  ✓ {table}")
    
    # Check if ranking_config was seeded
    result = session.execute(text("SELECT name FROM global_docs WHERE name='ranking_config'"))
    config = result.fetchone()
    
    if config:
        print("\n✓ ranking_config seeded in global_docs")
    else:
        print("\n✗ ranking_config NOT found in global_docs")
