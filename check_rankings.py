"""View current issue rankings from the leaderboard."""
from backend.core.db import get_session
from sqlalchemy import text

with get_session() as session:
    # Get top ranked issues
    result = session.execute(text("""
        SELECT 
            ti.issue_id,
            i.title,
            ti.overall_score,
            ti.dimension_scores,
            ti.is_active
        FROM tracked_issues ti
        JOIN issues i ON ti.issue_id = i.id
        WHERE ti.is_active = true
        ORDER BY ti.overall_score DESC
        LIMIT 20
    """)).fetchall()
    
    if not result:
        print("❌ No ranked issues found")
        print("   Rankings are created when issues go through the ranking agent")
    else:
        print(f"\n🏆 Top {len(result)} Ranked Issues\n")
        print(f"{'Rank':<6} {'Score':<8} {'Issue ID':<12} {'Title':<60}")
        print("=" * 90)
        
        for rank, (issue_id, title, score, dims, active) in enumerate(result, 1):
            title_short = title[:55] + "..." if len(title) > 55 else title
            print(f"{rank:<6} {score:<8.2f} {issue_id:<12} {title_short}")
        
        # Show dimension scores for top issue
        if result:
            top_id, top_title, top_score, top_dims, _ = result[0]
            print(f"\n📊 Top Issue Dimension Scores:")
            print(f"   Issue: {top_title}")
            for dim, score in top_dims.items():
                print(f"   {dim.capitalize()}: {score}/10")
