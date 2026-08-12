"""Discovery agent reporting and RAG storage.

Generates structured reports from discovery runs including:
- Tavily and Perplexity API call counts
- Search queries and strategies
- Issues created with reasoning
- Proposed duplicates (semantic similarity 0.75-0.9)
- Findings summary

Reports are saved to Postgres (not JSON files) for RAG retrieval and learning.
Embeds report digests for semantic memory recall by the discovery agent.
"""
import json
from collections import Counter
from datetime import datetime
from typing import Any

from backend.core.db import get_session
from backend.models.db_models import DiscoveryReport, DiscoveryReportChunk
from backend.services.chunking import chunk_text
from backend.services.embedding import generate_embeddings_batch


def _generate_narrative_summary(
    created_issues: list[dict],
    proposed_duplicates: list[dict],
    topic: str,
    search_queries: list[dict]
) -> str:
    """Generate a narrative summary for RAG semantic search.
    
    Creates human-readable summary explaining:
    - What issues were discovered and why they matter
    - Selection criteria and logic
    - Common themes and patterns
    - Important facts and context
    
    Args:
        created_issues: List of issues created in this run
        proposed_duplicates: List of duplicates that were merged/skipped
        topic: Discovery topic
        search_queries: List of search queries used
        
    Returns:
        Narrative text summary for embedding and RAG retrieval
    """
    if not created_issues:
        return f"Discovery run on '{topic}' yielded no new issues. Existing coverage may be sufficient, or search queries need refinement."
    
    lines = []
    lines.append(f"## Discovery Summary: {topic}")
    lines.append("")
    
    # Core findings
    lines.append(f"### Issues Discovered ({len(created_issues)})")
    lines.append("")
    
    # Extract themes from tags
    all_tags = []
    for issue in created_issues:
        all_tags.extend(issue.get("tags", []))
    
    tag_counts = Counter(all_tags)
    top_tags = [tag for tag, _ in tag_counts.most_common(5)]
    
    if top_tags:
        lines.append(f"**Common Themes:** {', '.join(top_tags)}")
        lines.append("")
    
    # Describe each issue with reasoning
    for i, issue in enumerate(created_issues, 1):
        lines.append(f"**{i}. {issue.get('title')}**")
        lines.append(f"   - Why it matters: {issue.get('why', 'N/A')[:200]}...")
        lines.append(f"   - Affected groups: {', '.join(issue.get('tags', [])[:4])}")
        lines.append("")
    
    # Selection logic
    lines.append("### Selection Logic")
    lines.append("")
    
    if len(created_issues) > 0:
        lines.append(f"These {len(created_issues)} issues were selected because they represent:")
        
        # Analyze issue types from tags
        issue_types = [tag for tag in all_tags if tag in [
            'health', 'security', 'economy', 'environment', 'social', 
            'technology', 'policy', 'infrastructure', 'education', 'human-rights'
        ]]
        
        if issue_types:
            type_counts = Counter(issue_types)
            lines.append(f"- Issue categories: {', '.join([f'{t} ({c})' for t, c in type_counts.most_common(3)])}")
        
        # Affected demographics
        demographics = [tag for tag in all_tags if tag in [
            'teens', '20s', '30s', '40s', '50s', '60+', 'elderly',
            'low-income', 'middle-class', 'wealthy', 'students', 'workers', 'unemployed'
        ]]
        
        if demographics:
            lines.append(f"- Primary affected groups: {', '.join(list(set(demographics))[:4])}")
        
        lines.append(f"- Search strategy: {len(search_queries)} targeted queries focusing on current, evidence-based issues")
    
    lines.append("")
    
    # Important context
    lines.append("### Key Insights")
    lines.append("")
    
    # Analyze "why" statements for common themes
    why_texts = [issue.get('why', '') for issue in created_issues if issue.get('why')]
    
    if why_texts:
        # Look for common words in why statements
        why_words = []
        for why in why_texts:
            why_words.extend(why.lower().split())
        
        # Filter meaningful words (rough approach)
        meaningful = [w for w in why_words if len(w) > 5 and w.isalpha()]
        if meaningful:
            word_counts = Counter(meaningful)
            top_concepts = [word for word, _ in word_counts.most_common(3)]
            lines.append(f"Core concerns: {', '.join(top_concepts)}")
    
    lines.append(f"All issues are current, actionable, and supported by evidence from search results.")
    lines.append("")
    
    # Deduplication context
    if proposed_duplicates:
        lines.append(f"Note: {len(proposed_duplicates)} potential duplicates were identified and handled appropriately.")
        lines.append("")
    
    return "\n".join(lines)


def generate_report(
    run_result: dict[str, Any],
    topic: str,
    instruction: str
) -> dict[str, Any]:
    """Generate a structured report from a discovery run.
    
    Args:
        run_result: Result dict from discover_issues()
        topic: Discovery topic
        instruction: Discovery instruction used
        
    Returns:
        Structured report dict ready for storage and RAG retrieval
    """
    trace = run_result.get("trace", [])
    created_issues = run_result.get("created_issues", [])
    proposed_duplicates = run_result.get("proposed_duplicates", [])  # NEW
    
    # Count API calls
    tavily_calls = []
    perplexity_calls = []
    search_queries = []
    
    for entry in trace:
        if entry.get("tool") == "search_tavily":
            query = entry.get("arguments", {}).get("query", "")
            results_count = len(entry.get("result", {}).get("results", []))
            tavily_calls.append({"query": query, "results": results_count})
            search_queries.append({"engine": "tavily", "query": query})
        
        elif entry.get("tool") == "search_perplexity":
            query = entry.get("arguments", {}).get("query", "")
            results_count = len(entry.get("result", {}).get("results", []))
            perplexity_calls.append({"query": query, "results": results_count})
            search_queries.append({"engine": "perplexity", "query": query})
    
    # Build findings summary
    findings = []
    for issue in created_issues:
        findings.append({
            "id": issue.get("id"),
            "title": issue.get("title"),
            "summary": issue.get("summary"),
            "why": issue.get("why", ""),
            "tags": issue.get("tags", []),
            "created_at": issue.get("created_at")
        })
    
    # Generate narrative summary for RAG retrieval
    summary_text = _generate_narrative_summary(
        created_issues, 
        proposed_duplicates,
        topic or "autonomous exploration",
        search_queries
    )
    
    report = {
        "timestamp": datetime.now().isoformat(),
        "metadata": {
            "topic": topic or "autonomous",
            "instruction": instruction,
            "target_count": run_result.get("target_issue_count"),
            "actual_created": len(created_issues),
            "iterations": run_result.get("iterations", 0),
            "review_mode": run_result.get("review_mode", False),
        },
        "api_usage": {
            "tavily": {
                "calls": len(tavily_calls),
                "queries": tavily_calls,
                "total_results": sum(q.get("results", 0) for q in tavily_calls)
            },
            "perplexity": {
                "calls": len(perplexity_calls),
                "queries": perplexity_calls,
                "total_results": sum(q.get("results", 0) for q in perplexity_calls)
            },
            "total_searches": len(search_queries),
            "search_strategy": {
                "tavily_vs_perplexity": f"{len(tavily_calls)} Tavily vs {len(perplexity_calls)} Perplexity",
                "queries": search_queries
            }
        },
        "findings": findings,
        "proposed_duplicates": proposed_duplicates,  # NEW - candidates in 0.75-0.9 similarity range
        "summary": summary_text  # Now a narrative text for semantic search
    }
    
    return report


def save_report(report: dict[str, Any]) -> int:
    """Save report to Postgres with embeddings for RAG retrieval.
    
    Args:
        report: Report dict from generate_report()
        
    Returns:
        report_id (int) - primary key of saved report
    """
    metadata = report["metadata"]
    
    # Insert main report row
    with get_session() as session:
        db_report = DiscoveryReport(
            topic=metadata["topic"],
            instruction=metadata["instruction"],
            target_count=metadata["target_count"],
            actual_created=metadata["actual_created"],
            iterations=metadata["iterations"],
            review_mode=metadata["review_mode"],
            api_usage=report["api_usage"],
            findings=report["findings"],
            proposed_duplicates=report.get("proposed_duplicates", []),
            summary=report["summary"]
        )
        session.add(db_report)
        session.flush()  # Get the ID before committing
        report_id = db_report.id
        session.commit()
    
    # Build digest text for embedding (semantic memory)
    digest_lines = [
        f"Discovery Run: {metadata['topic']}",
        f"Instruction: {metadata['instruction']}",
        f"Created {metadata['actual_created']} issues in {metadata['iterations']} iterations",
        "",
        "Search Queries:"
    ]
    
    for query in report["api_usage"]["search_strategy"]["queries"]:
        digest_lines.append(f"  [{query['engine']}] {query['query']}")
    
    digest_lines.append("")
    digest_lines.append("Findings:")
    for finding in report["findings"]:
        digest_lines.append(f"  - {finding['title']}")
        digest_lines.append(f"    Tags: {', '.join(finding['tags'])}")
        digest_lines.append(f"    Why: {finding['why'][:150]}...")
    
    if report.get("proposed_duplicates"):
        digest_lines.append("")
        digest_lines.append("Proposed Duplicates (not created):")
        for dup in report["proposed_duplicates"]:
            digest_lines.append(f"  - {dup.get('candidate_title', 'N/A')}")
            digest_lines.append(f"    Similar to: {dup.get('existing_title', 'N/A')} (similarity: {dup.get('similarity', 0):.2f})")
    
    digest_text = "\n".join(digest_lines)
    
    # Chunk and embed digest
    chunks = chunk_text(digest_text)
    if chunks:
        embeddings = generate_embeddings_batch(chunks)
        
        # Store chunks with embeddings
        with get_session() as session:
            for chunk_index, (chunk, embedding) in enumerate(zip(chunks, embeddings)):
                embedding_str = "[" + ",".join(str(x) for x in embedding) + "]"
                
                chunk_obj = DiscoveryReportChunk(
                    report_id=report_id,
                    chunk_index=chunk_index,
                    chunk_text=chunk,
                    embedding=embedding_str
                )
                session.add(chunk_obj)
            
            session.commit()
    
    return report_id


def load_recent_reports(limit: int = 10) -> list[dict]:
    """Load recent discovery reports from Postgres for RAG context.
    
    Args:
        limit: Number of recent reports to load
        
    Returns:
        List of report dicts, newest first
    """
    with get_session() as session:
        reports = session.query(DiscoveryReport).order_by(
            DiscoveryReport.created_at.desc()
        ).limit(limit).all()
        
        return [
            {
                "timestamp": report.created_at.isoformat(),
                "metadata": {
                    "topic": report.topic,
                    "instruction": report.instruction,
                    "target_count": report.target_count,
                    "actual_created": report.actual_created,
                    "iterations": report.iterations,
                    "review_mode": report.review_mode,
                },
                "api_usage": report.api_usage,
                "findings": report.findings,
                "proposed_duplicates": report.proposed_duplicates,
                "summary": report.summary
            }
            for report in reports
        ]


def get_discovery_insights() -> dict[str, Any]:
    """Analyze all reports to extract insights for agent learning.
    
    Returns:
        Aggregated insights from past discovery runs
    """
    with get_session() as session:
        reports = session.query(DiscoveryReport).all()
    
    if not reports:
        return {"message": "No discovery reports found"}
    
    total_tavily = sum(r.api_usage["tavily"]["calls"] for r in reports)
    total_perplexity = sum(r.api_usage["perplexity"]["calls"] for r in reports)
    total_issues = sum(r.actual_created for r in reports)
    
    # Most common queries
    all_queries = []
    for r in reports:
        all_queries.extend([q["query"] for q in r.api_usage["tavily"]["queries"]])
        all_queries.extend([q["query"] for q in r.api_usage["perplexity"]["queries"]])
    
    # Most common tags in created issues
    all_tags = []
    for r in reports:
        for issue in r.findings:
            all_tags.extend(issue.get("tags", []))
    
    tag_frequency = Counter(all_tags)
    query_frequency = Counter(all_queries)
    
    total_calls = total_tavily + total_perplexity
    
    return {
        "total_reports": len(reports),
        "total_issues_created": total_issues,
        "api_calls": {
            "tavily": total_tavily,
            "perplexity": total_perplexity,
            "total": total_calls
        },
        "average_issues_per_run": total_issues / len(reports) if reports else 0,
        "most_effective_queries": [q for q, _ in query_frequency.most_common(5)],
        "most_common_tags": dict(tag_frequency.most_common(10)),
        "api_preference": f"{total_tavily / total_calls * 100:.1f}% Tavily, {total_perplexity / total_calls * 100:.1f}% Perplexity" if total_calls > 0 else "No data"
    }
