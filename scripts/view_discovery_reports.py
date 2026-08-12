#!/usr/bin/env python3
"""View and analyze discovery reports.

Displays recent discovery run reports including:
- API usage (Tavily vs Perplexity calls)
- Search queries and strategies
- Created issues with summaries
- Aggregated insights from all runs

Usage:
    python scripts/view_discovery_reports.py              # Show recent reports
    python scripts/view_discovery_reports.py --insights   # Show aggregated insights
    python scripts/view_discovery_reports.py --limit 20   # Show 20 most recent
    python scripts/view_discovery_reports.py --json       # Raw JSON output
"""
import argparse
import json
import sys
from pathlib import Path
from typing import Any

# Add backend to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from backend.workflows.discovery_reports import load_recent_reports, get_discovery_insights


def print_report_summary(report: dict[str, Any], index: int = 1) -> None:
    """Print a formatted summary of a discovery report."""
    metadata = report.get("metadata", {})
    api_usage = report.get("api_usage", {})
    summary = report.get("summary", "")  # Now a text string
    
    print(f"\n{'='*70}")
    print(f"Report #{index}: {metadata.get('topic', 'unknown')}")
    print(f"{'='*70}")
    print(f"Timestamp: {report.get('timestamp', 'N/A')}")
    print(f"Target: {metadata.get('target_count')} issues | Actual: {metadata.get('actual_created')} created")
    print(f"Iterations: {metadata.get('iterations')} | Review Mode: {metadata.get('review_mode')}")
    
    print(f"\n📊 API Usage:")
    tavily = api_usage.get("tavily", {})
    perplexity = api_usage.get("perplexity", {})
    print(f"   Tavily: {tavily.get('calls')} calls → {tavily.get('total_results')} results")
    print(f"   Perplexity: {perplexity.get('calls')} calls → {perplexity.get('total_results')} results")
    print(f"   Total Searches: {api_usage.get('total_searches')}")
    
    search_strat = api_usage.get("search_strategy", {})
    if search_strat.get("queries"):
        print(f"\n🔍 Search Queries:")
        for q in search_strat["queries"][:5]:  # Show first 5
            print(f"   [{q['engine']}] {q['query']}")
        if len(search_strat["queries"]) > 5:
            print(f"   ... and {len(search_strat['queries']) - 5} more")
    
    findings = report.get("findings", [])
    if findings:
        print(f"\n📝 Issues Created ({len(findings)}):")
        for issue in findings[:3]:  # Show first 3
            tags_str = ", ".join(issue.get("tags", [])[:3])
            print(f"   • {issue['id']}: {issue['title'][:50]}...")
            print(f"     Tags: {tags_str}")
        if len(findings) > 3:
            print(f"   ... and {len(findings) - 3} more")
    
    # Print narrative summary
    if summary:
        print(f"\n📋 Discovery Summary:")
        # Print first 300 chars, or full text if short
        summary_preview = summary[:300] + "..." if len(summary) > 300 else summary
        print(f"   {summary_preview}")
        if len(summary) > 300:
            print(f"   (Full summary: {len(summary)} chars)")


def print_insights(insights: dict[str, Any]) -> None:
    """Print formatted aggregated insights."""
    print(f"\n{'='*70}")
    print("DISCOVERY INSIGHTS - Aggregated from All Runs")
    print(f"{'='*70}")
    
    if "message" in insights:
        print(f"\n⚠️  {insights['message']}")
        return
    
    print(f"\n📊 Statistics:")
    print(f"   Total Reports: {insights.get('total_reports', 0)}")
    print(f"   Total Issues Created: {insights.get('total_issues_created', 0)}")
    print(f"   Average Issues/Run: {insights.get('average_issues_per_run', 0):.1f}")
    
    api_calls = insights.get("api_calls", {})
    print(f"\n🔧 API Usage:")
    print(f"   Tavily Calls: {api_calls.get('tavily', 0)}")
    print(f"   Perplexity Calls: {api_calls.get('perplexity', 0)}")
    print(f"   Total Calls: {api_calls.get('total', 0)}")
    print(f"   Preference: {insights.get('api_preference', 'N/A')}")
    
    queries = insights.get("most_effective_queries", [])
    if queries:
        print(f"\n🔍 Most Effective Queries:")
        for i, q in enumerate(queries, 1):
            print(f"   {i}. {q}")
    
    tags = insights.get("most_common_tags", {})
    if tags:
        print(f"\n🏷️  Most Common Tags:")
        for tag, count in sorted(tags.items(), key=lambda x: x[1], reverse=True)[:10]:
            print(f"   {tag}: {count}")


def main():
    parser = argparse.ArgumentParser(description="View discovery reports and insights")
    parser.add_argument(
        "--insights",
        action="store_true",
        help="Show aggregated insights instead of recent reports"
    )
    parser.add_argument(
        "--limit",
        type=int,
        default=10,
        help="Number of recent reports to show (default: 10)"
    )
    parser.add_argument(
        "--json",
        action="store_true",
        help="Output raw JSON instead of formatted text"
    )
    
    args = parser.parse_args()
    
    if args.insights:
        # Show insights
        insights = get_discovery_insights()
        
        if args.json:
            print(json.dumps(insights, indent=2))
        else:
            print_insights(insights)
    else:
        # Show recent reports
        reports = load_recent_reports(limit=args.limit)
        
        if not reports:
            print("❌ No discovery reports found")
            print("   Run discovery first: python -m uvicorn backend.main:app --reload")
            print("   Then POST to /api/discovery endpoint")
            return
        
        if args.json:
            print(json.dumps(reports, indent=2))
        else:
            print(f"\n📋 Recent Discovery Reports ({len(reports)} found)")
            for i, report in enumerate(reports, 1):
                print_report_summary(report, i)
            
            # Show brief insights summary
            insights = get_discovery_insights()
            if insights.get("total_reports", 0) > len(reports):
                print(f"\n💡 View aggregated insights: python scripts/view_discovery_reports.py --insights")


if __name__ == "__main__":
    main()
