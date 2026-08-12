#!/usr/bin/env python3
"""Test discovery agent intelligence and Perplexity integration.

Verifies:
1. What model is being used (should be gpt-4o, not gpt-4o-mini)
2. Whether Perplexity API is configured and working
3. Tool descriptions that guide agent behavior
"""
import os
import sys

from backend.agents.discovery import agent
from backend.services import perplexity_service


def test_model_config():
    """Check which model the discovery agent is using."""
    print("="*70)
    print("DISCOVERY AGENT MODEL")
    print("="*70)
    print(f"Current model: {agent.DEFAULT_MODEL}")
    
    env_override = os.getenv("OPENAI_DISCOVERY_MODEL")
    if env_override:
        print(f"  Source: Environment variable OPENAI_DISCOVERY_MODEL={env_override}")
    else:
        print(f"  Source: Default (no env var set)")
    
    # Model intelligence comparison
    print("\nModel Intelligence Levels:")
    print("  • gpt-4o-mini    : ⚡ Fastest/cheapest, basic reasoning")
    print("  • gpt-4o         : 🧠 Balanced - intelligent + fast (RECOMMENDED)")
    print("  • gpt-4-turbo    : 🎯 Most intelligent, slower, expensive")
    
    if agent.DEFAULT_MODEL == "gpt-4o-mini":
        print("\n⚠️  WARNING: Using gpt-4o-mini (least intelligent)")
        print("   For smarter discovery, set: OPENAI_DISCOVERY_MODEL=gpt-4o")
    elif agent.DEFAULT_MODEL == "gpt-4o":
        print("\n✅ Using gpt-4o (recommended balance)")
    else:
        print(f"\n✅ Using {agent.DEFAULT_MODEL}")


def test_perplexity_config():
    """Check if Perplexity is configured."""
    print("\n" + "="*70)
    print("PERPLEXITY API CONFIGURATION")
    print("="*70)
    
    if perplexity_service.is_configured():
        print("✅ Perplexity API key is configured")
        
        # Test actual call
        print("\nTesting Perplexity search...")
        try:
            results = perplexity_service.search("What are the main challenges in AI safety?")
            print(f"✅ Perplexity search successful!")
            print(f"   Response length: {len(results[0]['content'])} chars")
            print(f"   Citations: {len(results[0]['citations'])} sources")
            print(f"   Preview: {results[0]['content'][:150]}...")
        except Exception as e:
            print(f"❌ Perplexity search failed: {e}")
    else:
        print("❌ Perplexity API key NOT configured")
        print("   Add to .env: PERPLEXITY_API_KEY=pplx-...")
        print("   Impact: Agent can only use Tavily (fast but less authoritative)")


def test_tool_descriptions():
    """Show tool descriptions that guide agent behavior."""
    print("\n" + "="*70)
    print("TOOL DESCRIPTIONS (Guide Agent Behavior)")
    print("="*70)
    
    for tool in agent.TOOLS:
        func = tool["function"]
        print(f"\n{func['name']}:")
        print(f"  {func['description']}")
    
    print("\n💡 Better tool descriptions = smarter tool choice")
    print("   Perplexity description should emphasize quality, evidence, validation")


def main():
    print("\n🧠 DISCOVERY AGENT INTELLIGENCE CHECK\n")
    
    test_model_config()
    test_perplexity_config()
    test_tool_descriptions()
    
    print("\n" + "="*70)
    print("RECOMMENDATIONS")
    print("="*70)
    
    issues = []
    if agent.DEFAULT_MODEL == "gpt-4o-mini":
        issues.append("⚠️  Upgrade to gpt-4o for better reasoning (set OPENAI_DISCOVERY_MODEL=gpt-4o)")
    
    if not perplexity_service.is_configured():
        issues.append("⚠️  Configure Perplexity for authoritative research with citations")
    
    if issues:
        for issue in issues:
            print(f"  {issue}")
    else:
        print("  ✅ All systems optimal!")
    
    print("\n" + "="*70)
    print()


if __name__ == "__main__":
    main()
