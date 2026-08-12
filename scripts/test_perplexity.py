#!/usr/bin/env python3
"""Test Perplexity API integration.

Tests:
1. Service configuration check
2. Basic search functionality
3. Compare Tavily vs Perplexity results
4. Discovery agent with Perplexity tool

Usage:
    python scripts/test_perplexity.py [--compare]
"""
import argparse
import json
import os
import sys
from pathlib import Path

# Load .env BEFORE importing backend modules
from dotenv import load_dotenv
load_dotenv()

# Add backend to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from backend.services import perplexity_service, search_service


def test_configuration():
    """Test if Perplexity API is configured."""
    print("\n" + "=" * 60)
    print("TEST 1: Configuration Check")
    print("=" * 60)
    
    perplexity_configured = perplexity_service.is_configured()
    tavily_configured = search_service.is_configured()
    
    print(f"Perplexity API: {'✅ Configured' if perplexity_configured else '❌ Not configured'}")
    print(f"Tavily API: {'✅ Configured' if tavily_configured else '❌ Not configured'}")
    
    if not perplexity_configured:
        print("\n⚠️  To configure Perplexity:")
        print("   1. Get API key from https://www.perplexity.ai/")
        print("   2. Add to .env: PERPLEXITY_API_KEY=your_key_here")
        return False
    
    return True


def test_basic_search():
    """Test basic Perplexity search."""
    print("\n" + "=" * 60)
    print("TEST 2: Basic Search")
    print("=" * 60)
    
    query = "artificial intelligence safety challenges 2026"
    print(f"\nQuery: {query}")
    
    try:
        results = perplexity_service.search(query)
        print(f"\n✅ Search successful")
        print(f"   Results: {len(results)}")
        
        if results:
            result = results[0]
            print(f"\n   Content preview: {result['content'][:200]}...")
            print(f"   Citations: {len(result.get('citations', []))} sources")
            if result.get('citations'):
                print(f"   First citation: {result['citations'][0]}")
        
        return True
        
    except Exception as e:
        print(f"\n❌ Search failed: {e}")
        return False


def test_compare_search():
    """Compare Tavily and Perplexity search results."""
    print("\n" + "=" * 60)
    print("TEST 3: Compare Tavily vs Perplexity")
    print("=" * 60)
    
    query = "climate change impacts 2026"
    print(f"\nQuery: {query}")
    
    try:
        comparison = perplexity_service.compare_search(query)
        
        tavily_results = comparison.get('tavily_results', [])
        perplexity_results = comparison.get('perplexity_results', [])
        
        print(f"\nTavily results: {len(tavily_results)}")
        if tavily_results:
            print(f"   Sample: {tavily_results[0].get('title', 'N/A')}")
        
        print(f"\nPerplexity results: {len(perplexity_results)}")
        if perplexity_results:
            result = perplexity_results[0]
            print(f"   Content length: {len(result['content'])} chars")
            print(f"   Citations: {len(result.get('citations', []))}")
        
        if 'tavily_error' in comparison:
            print(f"\n⚠️  Tavily error: {comparison['tavily_error']}")
        if 'perplexity_error' in comparison:
            print(f"\n⚠️  Perplexity error: {comparison['perplexity_error']}")
        
        print("\n✅ Comparison completed")
        return True
        
    except Exception as e:
        print(f"\n❌ Comparison failed: {e}")
        return False


def test_discovery_agent_tool():
    """Test that discovery agent can use Perplexity tool."""
    print("\n" + "=" * 60)
    print("TEST 4: Discovery Agent Tool Integration")
    print("=" * 60)
    
    # Import the discovery agent
    try:
        from backend.agents.discovery import agent
        
        # Check if Perplexity tool is in TOOLS
        tool_names = [
            t['function']['name']
            for t in agent.TOOLS
        ]
        
        has_perplexity = 'search_perplexity' in tool_names
        has_tavily = 'search_tavily' in tool_names
        
        print(f"\nDiscovery agent tools:")
        print(f"   search_tavily: {'✅' if has_tavily else '❌'}")
        print(f"   search_perplexity: {'✅' if has_perplexity else '❌'}")
        
        if has_perplexity:
            # Test the tool function directly
            try:
                result = agent._tool_search_perplexity("test query")
                print(f"\n✅ Tool function works")
                print(f"   Query: {result.get('query')}")
                print(f"   Results: {len(result.get('results', []))}")
                return True
            except Exception as e:
                print(f"\n❌ Tool function failed: {e}")
                return False
        else:
            print("\n❌ search_perplexity tool not found in TOOLS array")
            return False
        
    except Exception as e:
        print(f"\n❌ Discovery agent import failed: {e}")
        return False


def main():
    parser = argparse.ArgumentParser(description="Test Perplexity integration")
    parser.add_argument(
        "--compare",
        action="store_true",
        help="Run comparison test (requires both Tavily and Perplexity)"
    )
    
    args = parser.parse_args()
    
    print("\n🧪 Testing Perplexity Integration")
    
    # Test 1: Configuration
    if not test_configuration():
        print("\n⚠️  Skipping further tests - Perplexity not configured")
        sys.exit(1)
    
    # Test 2: Basic search
    if not test_basic_search():
        print("\n⚠️  Basic search failed - check API key and connectivity")
        sys.exit(1)
    
    # Test 3: Comparison (optional)
    if args.compare:
        test_compare_search()
    
    # Test 4: Discovery agent integration
    test_discovery_agent_tool()
    
    print("\n" + "=" * 60)
    print("✅ All tests completed")
    print("=" * 60)


if __name__ == "__main__":
    main()
