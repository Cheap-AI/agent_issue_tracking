#!/usr/bin/env python3
"""Scheduled discovery automation using rotating strategies.

This script runs discovery on a schedule with different strategies each day.
Strategies rotate to ensure comprehensive coverage across different domains.

Usage:
    python scripts/scheduled_discovery.py [--once] [--strategy-index N]
    
    --once: Run once and exit (for cron jobs)
    --strategy-index N: Run specific strategy (0-5)
"""
import argparse
import os
import sys
import time
from datetime import datetime
from pathlib import Path

# Add backend to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from backend.workflows.discover_issue import discover_issue


# Discovery strategies - rotates through these
STRATEGIES = [
    {
        "name": "Technology Issues",
        "topic": "technology",
        "instruction": "Find emerging technology issues affecting users, developers, or society",
        "target": 5,
        "iterations": 25
    },
    {
        "name": "Healthcare & Public Health",
        "topic": "healthcare",
        "instruction": "Explore healthcare access, public health challenges, and medical system issues",
        "target": 5,
        "iterations": 25
    },
    {
        "name": "Economic & Financial",
        "topic": "economy",
        "instruction": "Identify economic issues affecting workers, consumers, businesses, and markets",
        "target": 5,
        "iterations": 25
    },
    {
        "name": "Environment & Climate",
        "topic": "environment",
        "instruction": "Find environmental challenges, climate impacts, and sustainability issues",
        "target": 5,
        "iterations": 25
    },
    {
        "name": "Social & Policy",
        "topic": "society",
        "instruction": "Discover social issues, policy challenges, and community impacts",
        "target": 5,
        "iterations": 25
    },
    {
        "name": "Autonomous Gap-Filling",
        "topic": "",  # Fully autonomous
        "instruction": "Find underrepresented issues across all domains. Look for gaps in current coverage.",
        "target": 10,
        "iterations": 40
    }
]


def get_strategy_for_day() -> dict:
    """Get strategy based on day of week."""
    day_index = datetime.now().weekday()  # 0=Monday, 6=Sunday
    return STRATEGIES[day_index % len(STRATEGIES)]


def run_discovery(strategy: dict, dry_run: bool = False) -> dict:
    """Run discovery with given strategy."""
    print(f"\n{'=' * 60}")
    print(f"Strategy: {strategy['name']}")
    print(f"{'=' * 60}")
    print(f"Topic: {strategy['topic'] or 'Autonomous'}")
    print(f"Instruction: {strategy['instruction']}")
    print(f"Target: {strategy['target']} issues")
    print(f"Max iterations: {strategy['iterations']}")
    
    if dry_run:
        print("\n[DRY RUN] Would execute discovery with above parameters")
        return {"status": "dry_run", "strategy": strategy['name']}
    
    try:
        print(f"\n🚀 Starting discovery at {datetime.now().isoformat()}")
        
        result = discover_issue(
            topic=strategy['topic'],
            instruction=strategy['instruction'],
            target_issue_count=strategy['target'],
            max_iterations=strategy['iterations'],
            seed_created_issues=True,
            require_evaluation=True
        )
        
        created = result.get('created_issues', [])
        print(f"\n✅ Discovery completed successfully")
        print(f"   Created: {len(created)} issues")
        print(f"   Iterations: {result.get('iterations', 0)}")
        print(f"   Run count today: {result.get('runs_today', 0)}")
        
        if created:
            print("\n📋 Created issues:")
            for issue in created:
                print(f"   - {issue['id']}: {issue['title']}")
        
        return result
        
    except Exception as e:
        print(f"\n❌ Discovery failed: {e}")
        return {"status": "error", "error": str(e)}


def main():
    parser = argparse.ArgumentParser(description="Scheduled discovery automation")
    parser.add_argument(
        "--once",
        action="store_true",
        help="Run once and exit (for cron jobs)"
    )
    parser.add_argument(
        "--strategy-index",
        type=int,
        choices=range(len(STRATEGIES)),
        help=f"Run specific strategy (0-{len(STRATEGIES)-1})"
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Show what would run without executing"
    )
    parser.add_argument(
        "--schedule",
        type=str,
        default="02:00",
        help="Time to run daily (HH:MM format, default: 02:00)"
    )
    
    args = parser.parse_args()
    
    # Validate environment
    if not os.getenv("DATABASE_URL"):
        print("❌ ERROR: DATABASE_URL not configured in .env")
        sys.exit(1)
    
    if not os.getenv("TAVILY_API_KEY") and not os.getenv("PERPLEXITY_API_KEY"):
        print("⚠️  WARNING: Neither TAVILY_API_KEY nor PERPLEXITY_API_KEY configured")
        print("   Discovery agent needs at least one search API")
    
    # Select strategy
    if args.strategy_index is not None:
        strategy = STRATEGIES[args.strategy_index]
    else:
        strategy = get_strategy_for_day()
    
    if args.once:
        # Run once and exit (for cron)
        run_discovery(strategy, dry_run=args.dry_run)
        return
    
    # Continuous mode with daily schedule
    print(f"🤖 Scheduled Discovery Automation")
    print(f"   Schedule: Daily at {args.schedule}")
    print(f"   Strategies: {len(STRATEGIES)} rotating strategies")
    print(f"\nPress Ctrl+C to stop\n")
    
    try:
        import schedule
        
        hour, minute = args.schedule.split(":")
        schedule_time = f"{hour}:{minute}"
        
        def scheduled_job():
            strategy = get_strategy_for_day()
            run_discovery(strategy)
        
        schedule.every().day.at(schedule_time).do(scheduled_job)
        
        print(f"⏰ Next run: {schedule.next_run()}")
        
        while True:
            schedule.run_pending()
            time.sleep(60)  # Check every minute
            
    except KeyboardInterrupt:
        print("\n\n👋 Stopping scheduled discovery")
    except ImportError:
        print("\n❌ ERROR: 'schedule' package not installed")
        print("   Install with: pip install schedule")
        sys.exit(1)


if __name__ == "__main__":
    main()
