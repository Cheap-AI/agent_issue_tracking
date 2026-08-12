"""Direct test of discovery agent to see logging output."""
import logging
import sys

# Configure logging to see output
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[logging.StreamHandler(sys.stdout)]
)

from backend.agents.discovery.agent import discover_issues

# Run discovery directly with minimal config
result = discover_issues(
    topic="test logging",
    instruction="",
    target_issue_count=1,
    max_iterations=5,  # Give it enough iterations!
    seed_created_issues=False,  # Skip seeding
    memory_context="No prior memory"
)

print("\n" + "="*70)
print("FINAL RESULT:")
print(f"Created: {len(result['created_issues'])} issues")
print(f"Proposed: {len(result['proposed_issues'])} issues")  
print(f"Iterations: {result['iterations']}")
print(f"Final message: {result['final_message']}")
print("="*70)
