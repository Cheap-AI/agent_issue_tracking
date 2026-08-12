#!/usr/bin/env python3
"""Test the events collection endpoint."""
import requests
import json

BASE_URL = "http://127.0.0.1:8000/api"

def test_events_endpoint():
    """Test creating an issue and collecting events for it."""
    
    # Step 1: Create a test issue
    print("Creating test issue...")
    issue_data = {
        "title": "AI Safety Research",
        "summary": "Research into safety and alignment of large language models",
        "why": "Ensuring AI systems remain safe and aligned with human values"
    }
    
    response = requests.post(f"{BASE_URL}/issues", json=issue_data)
    if response.status_code != 201:
        print(f"Failed to create issue: {response.status_code}")
        print(f"Response: {response.text}")
        return False
    
    print(f"Status code: {response.status_code}")
    print(f"Response: {response.text}")
    
    response_data = response.json()
    issue = response_data.get("issue", response_data)
    issue_id = issue.get("id", issue.get("issue_id"))
    print(f"✓ Created issue: {issue_id} - {issue['title']}")
    
    # Step 2: Trigger events collection
    print(f"\nTriggering events collection for {issue_id}...")
    events_response = requests.post(
        f"{BASE_URL}/issues/{issue_id}/events",
        params={"search_query": "AI safety research alignment"}
    )
    
    if events_response.status_code != 200:
        print(f"Failed to trigger events: {events_response.status_code} {events_response.text}")
        return False
    
    result = events_response.json()
    print(f"✓ Events collection triggered: {result['status']}")
    print(f"  Message: {result.get('message', '')}")
    
    return True

if __name__ == "__main__":
    try:
        success = test_events_endpoint()
        if success:
            print("\n✅ Events endpoint test passed!")
        else:
            print("\n❌ Events endpoint test failed!")
    except Exception as e:
        print(f"❌ Error: {e}")
