import os
from typing import List, Literal
from openai import OpenAI
from pydantic import BaseModel, Field

# 1. Initialize the official OpenAI SDK (Reads OPENAI_API_KEY from environment)
client = OpenAI(api_key=os.environ.get("OPENAI_API_KEY", "your-key-here"))

# 2. Define the exact, unbreakable JSON data structure using Pydantic
class TimelineEvent(BaseModel):
    date: str = Field(description="The date of the occurrence (YYYY-MM-DD format if available, or relative timeline text)")
    event_description: str = Field(description="Clear, noise-free description of what actually happened.")

class StructuredIssue(BaseModel):
    issue_id: str = Field(description="Unique identifier, e.g., ISSUE-2026-CHIPWAR")
    title: str = Field(description="A clean, impactful title representing the macro issue.")
    category: Literal["Geopolitics", "Technology & Innovation", "Climate & Environment", "Macroeconomics"]
    urgency_status: Literal["🔴 Critical", "🟡 Guarded", "🟢 Optimistic"]
    ranking_score: float = Field(description="A score from 1.0 to 10.0 based on structural shift potential and chain-of-events potential.")
    judgment_basis: str = Field(description="The explicit engineering reasoning on why this constitutes a macro issue based on scale or cascade potential.")
    fun_executive_metaphor: str = Field(description="A witty, engaging, or slightly humorous 1-sentence metaphor explaining this issue to keep the user entertained.")
    root_cause: str = Field(description="The underlying trigger or historical fuel behind this issue.")
    timeline: List[TimelineEvent] = Field(description="Chronological chain of events tracking how this issue developed.")
    downstream_consequences: List[str] = Field(description="1st and 2nd-order ripple effects this will cause over the next 1-6 months.")

# 3. The Core Evaluation Function
def analyze_ingested_signals(raw_news_payload: str) -> StructuredIssue:
    system_prompt = """
    You are the Chief Intelligence Analyst for an elite, noise-free strategic radar platform.
    Your job is to read raw data signals and extract/define structural 'Issues'.
    
    You must evaluate the data using 3 criteria:
    1. Scope & Scale: Does it impact industries, nations, or global ecosystems?
    2. Cascade Potential: Will it trigger 2nd-order downstream effects over the next 1-6 months?
    3. Structural Shift: Does it mark a paradigm turning point (crisis or corporate breakthrough)?
    
    If it fits, extract the data into the requested JSON schema. Include a witty, engaging 'fun_executive_metaphor' to reduce cognitive fatigue for the reader.
    """

    # Enforce strict JSON object output matching our Pydantic model
    completion = client.beta.chat.completions.parse(
        model="gpt-4o-mini",  # Highly cost-efficient, fast, and reliable for structure
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": f"Analyze these raw data signals:\n\n{raw_news_payload}"}
        ],
        response_format=StructuredIssue,
    )
    
    return completion.choices[0].message.parsed

# 4. Local Execution Test (Simulating raw incoming data)
if __name__ == "__main__":
    # Sample incoming raw text snippet containing environmental tech innovation news
    simulated_news = """
    May 14, 2026 - Heliostat Energy Labs announced a massive breakthrough in solid-state grid batteries, achieving 4x energy density. 
    June 02, 2026 - EU lawmakers passed a sudden green energy mandate accelerating coal phaseouts by 3 years due to surging battery efficiency. 
    July 10, 2026 - Mining conglomerates report an immediate 15% drop in lithium market spot prices as the new solid-state tech shifts dependencies toward abundant iron-silicon baselines.
    """
    
    print("⏳ AI Engine analyzing raw signals and mapping dependencies...")
    try:
        analyzed_output = analyze_ingested_signals(simulated_news)
        
        # This print proves that the output is now a clean Python object/JSON ready for a database
        print("\n✅ Analysis Complete! Structured JSON Result:")
        print(analyzed_output.model_dump_json(indent=2))
        
    except Exception as e:
        print(f"\n❌ Error during execution: {e}")
        print("Please ensure your OPENAI_API_KEY environment variable is configured correctly.")
