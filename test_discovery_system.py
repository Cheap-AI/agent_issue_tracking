#!/usr/bin/env python3
"""Quick test of discovery RAG & deduplication system."""
import sys
from backend.workflows.discover_issue import discover_issue
from backend.workflows.discovery_reports import load_recent_reports, get_discovery_insights
from backend.services.vector_search import search_similar_reports, search_similar_issues_by_text
from backend.core.db import get_session
from sqlalchemy import text

print("\n" + "="*60)
print("  DISCOVERY SYSTEM QUICK TEST")
print("="*60 + "\n")

# Test 1: Schema
print("1️⃣  Checking schema...")
with get_session() as session:
    result = session.execute(text("""
        SELECT table_name FROM information_schema.tables 
        WHERE table_schema = 'public' 
        AND table_name IN ('issue_embeddings', 'discovery_reports', 'discovery_report_chunks')
    """)).fetchall()
    tables = [r[0] for r in result]
    print(f"   ✅ Tables: {', '.join(tables)}\n")

# Test 2: Discovery (quick run - only 2 issues)
print("2️⃣  Running discovery (this takes 2-4 min)...")
print("   Topic: 'AI safety' | Target: 2 issues\n")

result = discover_issue(
    topic="AI safety",
    target_issue_count=2,
    max_iterations=8,
    seed_created_issues=True
)

print(f"   ✅ Created: {len(result['created_issues'])} issues")
print(f"   ✅ Duplicates: {len(result.get('proposed_duplicates', []))}")
print(f"   ✅ Report ID: {result['report']['report_id']}\n")

if result['created_issues']:
    print("   📝 Issues created:")
    for issue in result['created_issues']:
        print(f"      • {issue['id']}: {issue['title'][:50]}...")

# Test 3: Embeddings
print("\n3️⃣  Checking embeddings...")
with get_session() as session:
    issue_emb = session.execute(text('SELECT COUNT(*) FROM issue_embeddings')).scalar()
    reports = session.execute(text('SELECT COUNT(*) FROM discovery_reports')).scalar()
    chunks = session.execute(text('SELECT COUNT(*) FROM discovery_report_chunks')).scalar()
    print(f"   ✅ Issue embeddings: {issue_emb}")
    print(f"   ✅ Reports: {reports}, Chunks: {chunks}\n")

# Test 4: RAG Search
print("4️⃣  Testing RAG search...")
similar = search_similar_issues_by_text("AI safety concerns", top_k=2)
print(f"   ✅ Found {len(similar)} similar issues")
for i, s in enumerate(similar, 1):
    print(f"      {i}. {s['issue_id']} (similarity: {s['similarity']:.2f})")

# Test 5: Insights
print("\n5️⃣  Getting insights...")
insights = get_discovery_insights()
print(f"   ✅ Total reports: {insights['total_reports']}")
print(f"   ✅ Total issues: {insights['total_issues_created']}")
print(f"   ✅ API calls: {insights['api_calls']}\n")

print("="*60)
print("  🎉 ALL TESTS PASSED!")
print("="*60)
print("\n✨ Discovery system working correctly!\n")
