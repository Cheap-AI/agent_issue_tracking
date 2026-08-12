#!/usr/bin/env python3
"""Test tags feature and autonomous discovery mode."""
import requests
import json

BASE_URL = "http://127.0.0.1:8000/api"

def test_tags_api():
    """Test creating an issue with tags via API."""
    print("=" * 60)
    print("TEST 1: Create issue with tags via API")
    print("=" * 60)
    
    issue_data = {
        "title": "Rising College Tuition Costs",
        "summary": "College tuition has increased 180% over the past 20 years, outpacing inflation and wage growth",
        "why": "Impacts millions of students and families, creating debt burden and limiting access to education",
        "tags": ["students", "20s-30s", "middle-class", "low-income", "education", "economy"]
    }
    
    response = requests.post(f"{BASE_URL}/issues", json=issue_data)
    if response.status_code != 201:
        print(f"❌ Failed to create issue: {response.status_code}")
        print(f"   Response: {response.text}")
        return False
    
    result = response.json()
    issue = result.get("issue", result)
    
    print(f"✅ Created issue: {issue['id']}")
    print(f"   Title: {issue['title']}")
    print(f"   Tags: {', '.join(issue.get('tags', []))}")
    
    # Verify tags were saved
    get_response = requests.get(f"{BASE_URL}/issues/{issue['id']}")
    if get_response.status_code == 200:
        fetched = get_response.json()["issue"]
        if fetched.get("tags") == issue_data["tags"]:
            print(f"✅ Tags verified after fetch")
        else:
            print(f"❌ Tags mismatch: {fetched.get('tags')} != {issue_data['tags']}")
            return False
    
    return True


def test_autonomous_discovery():
    """Test discovery agent with no topic (autonomous mode)."""
    print("\n" + "=" * 60)
    print("TEST 2: Autonomous Discovery (no topic)")
    print("=" * 60)
    
    discovery_data = {
        # No topic - fully autonomous
        "instruction": "Find 2 distinct issues that are underrepresented in current coverage",
        "target_issue_count": 2,
        "max_iterations": 10,
        "seed_created_issues": False
    }
    
    print(f"Triggering autonomous discovery...")
    print(f"  Instruction: {discovery_data['instruction']}")
    print(f"  Target: {discovery_data['target_issue_count']} issues")
    
    response = requests.post(f"{BASE_URL}/discovery", json=discovery_data)
    
    if response.status_code != 200:
        print(f"❌ Discovery failed: {response.status_code}")
        print(f"   Response: {response.text}")
        return False
    
    result = response.json()
    print(f"✅ Discovery triggered successfully")
    print(f"   Status: {result.get('status', 'unknown')}")
    
    return True


def test_focused_discovery():
    """Test discovery agent with optional topic hint."""
    print("\n" + "=" * 60)
    print("TEST 3: Focused Discovery (with topic hint)")
    print("=" * 60)
    
    discovery_data = {
        "topic": "technology",  # Optional hint
        "instruction": "",  # Agent builds instruction from topic
        "target_issue_count": 1,
        "max_iterations": 5,
        "seed_created_issues": False
    }
    
    print(f"Triggering focused discovery...")
    print(f"  Topic hint: {discovery_data['topic']}")
    print(f"  Target: {discovery_data['target_issue_count']} issue")
    
    response = requests.post(f"{BASE_URL}/discovery", json=discovery_data)
    
    if response.status_code != 200:
        print(f"❌ Discovery failed: {response.status_code}")
        print(f"   Response: {response.text}")
        return False
    
    result = response.json()
    print(f"✅ Discovery triggered successfully")
    print(f"   Status: {result.get('status', 'unknown')}")
    
    return True


if __name__ == "__main__":
    try:
        print("\n🚀 Testing Tags & Autonomous Discovery\n")
        
        test1 = test_tags_api()
        test2 = test_autonomous_discovery()
        test3 = test_focused_discovery()
        
        print("\n" + "=" * 60)
        print("TEST SUMMARY")
        print("=" * 60)
        print(f"Tags API: {'✅ PASS' if test1 else '❌ FAIL'}")
        print(f"Autonomous Discovery: {'✅ PASS' if test2 else '❌ FAIL'}")
        print(f"Focused Discovery: {'✅ PASS' if test3 else '❌ FAIL'}")
        
        if test1 and test2 and test3:
            print("\n🎉 All tests passed!")
        else:
            print("\n⚠️  Some tests failed")
            
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()
