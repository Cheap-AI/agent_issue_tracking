#!/usr/bin/env python3
"""Gap-analysis discovery automation.

Analyzes the current issue database to identify gaps in coverage,
then runs targeted discovery to fill those gaps.

Analyzes:
- Tag distribution (age groups, socioeconomic, interest, type)
- Domain coverage (technology, health, economy, etc.)
- Temporal coverage (recent vs older issues)

Usage:
    python scripts/gap_analysis_discovery.py [--dry-run] [--target-per-gap N]
"""
import argparse
import os
import sys
from collections import Counter
from datetime import datetime, timedelta
from pathlib import Path

# Add backend to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from backend.core.issue import list_issues
from backend.workflows.discover_issue import discover_issue


# Expected coverage targets
TAG_TARGETS = {
    # Age groups - should have reasonable representation
    "age": ["teens", "20s-30s", "40s-50s", "60+", "elderly"],
    
    # Socioeconomic - broad coverage needed
    "socioeconomic": ["low-income", "middle-class", "wealthy", "students", "workers", "unemployed"],
    
    # Issue types - comprehensive domain coverage
    "type": [
        "health", "security", "economy", "environment", "social",
        "technology", "policy", "infrastructure", "education", "human-rights"
    ]
}


def analyze_gaps(issues: list[dict]) -> dict:
    """Analyze issue coverage and identify gaps."""
    print("\n📊 Analyzing issue coverage...")
    
    if not issues:
        return {
            "total_issues": 0,
            "gaps": ["No issues found - need comprehensive discovery across all domains"]
        }
    
    # Count tags
    all_tags = []
    for issue in issues:
        all_tags.extend(issue.get("tags", []))
    
    tag_counts = Counter(all_tags)
    
    # Analyze recency
    now = datetime.now()
    recent_issues = [
        i for i in issues
        if datetime.fromisoformat(i["created_at"].replace("Z", "+00:00")) > now - timedelta(days=7)
    ]
    
    # Find gaps
    gaps = []
    
    # Check tag coverage
    for category, expected_tags in TAG_TARGETS.items():
        for tag in expected_tags:
            count = tag_counts.get(tag, 0)
            if count == 0:
                gaps.append(f"Missing coverage: {tag} ({category})")
            elif count < 2:
                gaps.append(f"Low coverage: {tag} ({category}) - only {count} issue(s)")
    
    # Check recency
    if len(recent_issues) < 5:
        gaps.append(f"Low recent activity: only {len(recent_issues)} issues in last 7 days")
    
    print(f"\n   Total issues: {len(issues)}")
    print(f"   Recent issues (7 days): {len(recent_issues)}")
    print(f"   Unique tags: {len(tag_counts)}")
    print(f"   Gaps identified: {len(gaps)}")
    
    if gaps:
        print("\n   Top gaps:")
        for gap in gaps[:5]:
            print(f"      - {gap}")
    
    return {
        "total_issues": len(issues),
        "recent_issues": len(recent_issues),
        "tag_counts": dict(tag_counts),
        "gaps": gaps
    }


def generate_gap_filling_instructions(gaps: list[str]) -> list[dict]:
    """Generate targeted discovery instructions to fill gaps."""
    strategies = []
    
    # Group gaps by category
    missing_tags = [g for g in gaps if "Missing coverage:" in g]
    low_coverage = [g for g in gaps if "Low coverage:" in g]
    
    # Strategy 1: Fill missing tags with focused search
    if missing_tags[:3]:  # Top 3 missing
        tags_to_fill = [g.split(": ")[1].split(" (")[0] for g in missing_tags[:3]]
        strategies.append({
            "name": "Fill Missing Coverage",
            "topic": "",
            "instruction": f"Find issues that affect these underrepresented groups: {', '.join(tags_to_fill)}. Be specific and evidence-based.",
            "target": 3,
            "iterations": 20
        })
    
    # Strategy 2: Boost low coverage areas
    if low_coverage[:2]:  # Top 2 low coverage
        tags_to_boost = [g.split(": ")[1].split(" (")[0] for g in low_coverage[:2]]
        strategies.append({
            "name": "Boost Low Coverage",
            "topic": "",
            "instruction": f"Explore additional issues related to: {', '.join(tags_to_boost)}. Look for different angles and contexts.",
            "target": 2,
            "iterations": 20
        })
    
    # Strategy 3: General autonomous exploration if few strategies
    if len(strategies) < 2:
        strategies.append({
            "name": "Autonomous Exploration",
            "topic": "",
            "instruction": "Autonomously explore diverse domains to expand issue coverage. Focus on areas with current gaps.",
            "target": 5,
            "iterations": 30
        })
    
    return strategies


def run_gap_filling_discovery(dry_run: bool = False, target_per_gap: int = 3):
    """Run gap-analysis-driven discovery."""
    print("\n" + "=" * 60)
    print("GAP ANALYSIS DISCOVERY")
    print("=" * 60)
    
    # Step 1: Analyze current issues
    issues = list_issues()
    analysis = analyze_gaps(issues)
    
    if not analysis["gaps"]:
        print("\n✅ No significant gaps found - coverage is good!")
        return
    
    # Step 2: Generate strategies
    strategies = generate_gap_filling_instructions(analysis["gaps"])
    
    print(f"\n🎯 Generated {len(strategies)} gap-filling strategies:")
    for i, strategy in enumerate(strategies, 1):
        print(f"\n   {i}. {strategy['name']}")
        print(f"      Instruction: {strategy['instruction']}")
        print(f"      Target: {strategy['target']} issues")
    
    if dry_run:
        print("\n[DRY RUN] Would execute these strategies")
        return
    
    # Step 3: Run strategies
    print("\n🚀 Executing gap-filling discovery...\n")
    
    all_results = []
    for i, strategy in enumerate(strategies, 1):
        print(f"\n{'─' * 60}")
        print(f"Strategy {i}/{len(strategies)}: {strategy['name']}")
        print(f"{'─' * 60}")
        
        try:
            result = discover_issue(
                topic=strategy['topic'],
                instruction=strategy['instruction'],
                target_issue_count=strategy['target'],
                max_iterations=strategy['iterations'],
                seed_created_issues=True
            )
            
            created = result.get('created_issues', [])
            print(f"\n   ✅ Created {len(created)} issues")
            all_results.append(result)
            
        except Exception as e:
            print(f"\n   ❌ Failed: {e}")
    
    # Summary
    total_created = sum(len(r.get('created_issues', [])) for r in all_results)
    print(f"\n{'=' * 60}")
    print(f"SUMMARY")
    print(f"{'=' * 60}")
    print(f"   Total issues created: {total_created}")
    print(f"   Strategies executed: {len(all_results)}")
    print(f"   Original gaps: {len(analysis['gaps'])}")


def main():
    parser = argparse.ArgumentParser(description="Gap-analysis discovery automation")
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Show analysis and planned strategies without executing"
    )
    parser.add_argument(
        "--target-per-gap",
        type=int,
        default=3,
        help="Target issues per identified gap (default: 3)"
    )
    
    args = parser.parse_args()
    
    # Validate environment
    if not os.getenv("DATABASE_URL"):
        print("❌ ERROR: DATABASE_URL not configured in .env")
        sys.exit(1)
    
    run_gap_filling_discovery(
        dry_run=args.dry_run,
        target_per_gap=args.target_per_gap
    )


if __name__ == "__main__":
    main()
