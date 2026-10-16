"""
🌱 Seed Issue Research

Automatically seed research content for newly created issues.
Finds relevant information and creates research component.

Usage:
    python -m scripts.discovery.discovery_seed_research

    python -m scripts.discovery.discovery_seed_research --issue iss-0001

    python -m scripts.discovery.discovery_seed_research --batch

Output:
    - Issues processed
    - Research content generated
    - Sources retrieved
"""

Run manually (requires TAVILY_API_KEY set in .env):

    python -m scripts.seed_research
"""

from api.database import init_db
from api.index import perform_research

SEED_TOPIC = "give me 10 most important issues for the last 7 days"


def main() -> None:
    init_db()
    result = perform_research(SEED_TOPIC, max_results=10)
    print(f"Status: {result['status']}")
    print(f"Summary:\n{result['summary']}")
    print(f"Sources ({len(result['sources'])}):")
    for source in result["sources"]:
        print(f"  - {source}")


if __name__ == "__main__":
    main()
