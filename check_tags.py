#!/usr/bin/env python3
"""Check tag format of recent issues."""
from backend.core.db import get_session
from sqlalchemy import text

with get_session() as session:
    result = session.execute(text("""
        SELECT id, title, tags 
        FROM issues 
        ORDER BY created_at DESC 
        LIMIT 5
    """)).fetchall()
    
    print("\n=== RECENT ISSUES AND TAGS ===\n")
    for row in result:
        print(f"ID: {row[0]}")
        print(f"Title: {row[1]}")
        print(f"Tags: {row[2]}")
        print(f"Tag Count: {len(row[2])}")
        print(f"Tag Type: {type(row[2])}")
        print()
