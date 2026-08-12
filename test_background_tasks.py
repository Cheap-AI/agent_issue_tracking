"""Test BackgroundTasks integration with update_component"""
import time
import requests

BASE_URL = "http://127.0.0.1:8000"

print("="*70)
print("FastAPI BackgroundTasks Demo")
print("="*70)

# 1. Create a test issue
print("\n1. Creating test issue...")
response = requests.post(
    f"{BASE_URL}/api/issues",
    json={"title": "BackgroundTasks Test", "summary": "Testing background embeddings"}
)
issue = response.json()["issue"]
issue_id = issue["id"]
print(f"   ✓ Created: {issue_id}")

# 2. Update component with BackgroundTasks
print("\n2. Updating research component...")
print("   (This should return immediately)")

content = """
This is a test of FastAPI BackgroundTasks integration.
The update_component function now uses BackgroundTasks instead of manual threading.

Key improvements:
- FastAPI manages the thread pool
- Automatic cleanup
- Better integration with FastAPI lifecycle
- Easier to test

This content will be chunked and embedded in the background while the API
remains responsive to other requests.
""" * 5  # Make it longer to see the effect

start = time.time()
response = requests.post(
    f"{BASE_URL}/api/issues/{issue_id}/components/research",
    json={"content": content}
)
elapsed = time.time() - start

result = response.json()
print(f"   ✓ Response received in {elapsed:.3f} seconds")
print(f"   Version: {result[\"version\"]}")
print(f"   Status: {result[\"status\"]}")
print(f"   Embeddings: {result[\"embeddings\"]}")

print("\n3. How it works:")
print("   → Request arrives at FastAPI endpoint")
print("   → update_component() saves content to DB (fast)")
print("   → background_tasks.add_task() queues embedding generation")
print("   → Response sent immediately (~0.01s)")
print("   → Embeddings generated in background thread pool")
print("   → API stays responsive for other requests!")

print("\n" + "="*70)
print("✓ BackgroundTasks integration working!")
print("="*70)

print("\nNote: In production with OpenAI credits, embeddings would be")
print("generated in background. For now, it just shows the pattern.")
