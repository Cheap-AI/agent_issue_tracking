"""Summary Agent: Generate concise summaries from research.

This agent:
1. Reads the latest research component
2. Uses GPT-4 to create a concise executive summary
3. Saves the summary as a versioned component
"""
import os

from openai import OpenAI

from backend.core.knowledge import update_component, read_current


# Initialize OpenAI client
client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))


SYSTEM_PROMPT = """You are a summary agent for an AI-native Issue Intelligence Platform.

Your role is to create concise, executive-level summaries of technical issues.

A good summary should:
- Be 2-4 paragraphs maximum
- Lead with the most critical information
- Include: what, when, who's affected, severity, current status
- Be accessible to non-technical stakeholders
- Avoid jargon where possible
- Highlight key numbers (users affected, downtime, etc.)

Format as clean markdown without excessive headings."""


def generate_summary(issue_id: str) -> dict:
    """Generate a summary from the issue's research component.
    
    Args:
        issue_id: Issue to summarize
        
    Returns:
        Dict with keys: version, summary_content
    """
    # Step 1: Get the latest research
    research = read_current(issue_id, "research")
    
    if not research:
        raise ValueError(f"No research found for issue {issue_id}. Research must be completed first.")
    
    research_version, research_content = research
    
    # Step 2: Call GPT-4 to create summary
    user_prompt = f"""Based on the research below, create a concise executive summary.

Research Content:
{research_content}

Create a 2-4 paragraph summary that captures:
1. What the issue is (one sentence)
2. Impact and severity
3. Current status and any resolution
4. Key dates/timeline (if applicable)

Keep it concise and executive-friendly."""

    try:
        response = client.chat.completions.create(
            model="gpt-4",
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": user_prompt}
            ],
            temperature=0.5,
            max_tokens=800
        )
        
        summary_content = response.choices[0].message.content
        
    except Exception as e:
        # Fallback if API fails
        summary_content = f"Summary generation failed: {e}\n\nFirst 500 chars of research:\n{research_content[:500]}..."
    
    # Step 3: Save summary as new version
    version = update_component(
        issue_id=issue_id,
        component="summary",
        new_content=summary_content,
        background_tasks=None  # Sync mode for agent workflows
    )
    
    return {
        "version": version,
        "summary_content": summary_content,
        "research_version": research_version
    }
