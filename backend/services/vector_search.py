"""Vector similarity search using pgvector."""
from sqlalchemy import text

from backend.core.db import get_session
from backend.services.embedding import generate_embedding


def search_similar_issues_by_text(
    candidate_text: str,
    top_k: int = 5,
    exclude_issue_id: str | None = None
) -> list[dict]:
    """Search for existing issues similar to a candidate text (for deduplication).
    
    Args:
        candidate_text: Combined text from title + summary + why of candidate issue
        top_k: Number of similar issues to return (default 5)
        exclude_issue_id: Optional issue ID to exclude from results
        
    Returns:
        List of dicts with keys: issue_id, title, similarity (0-1, higher is more similar)
    """
    # Generate embedding for candidate
    query_embedding = generate_embedding(candidate_text)
    
    # Convert to PostgreSQL array format
    embedding_str = "[" + ",".join(str(x) for x in query_embedding) + "]"
    
    # Build WHERE clause
    where_sql = ""
    params = {"embedding": embedding_str, "top_k": top_k}
    
    if exclude_issue_id:
        where_sql = "WHERE ie.issue_id != :exclude_issue_id"
        params["exclude_issue_id"] = exclude_issue_id
    
    # Query using cosine similarity (1 - cosine_distance)
    sql = f"""
        SELECT 
            ie.issue_id,
            i.title,
            1 - (ie.embedding <=> CAST(:embedding AS vector)) AS similarity
        FROM issue_embeddings ie
        JOIN issues i ON ie.issue_id = i.id
        {where_sql}
        ORDER BY ie.embedding <=> CAST(:embedding AS vector)
        LIMIT :top_k
    """
    
    with get_session() as session:
        result = session.execute(text(sql), params)
        rows = result.fetchall()
        
        return [
            {
                "issue_id": row[0],
                "title": row[1],
                "similarity": float(row[2]),
            }
            for row in rows
        ]


def store_issue_embedding(
    issue_id: str,
    title: str,
    summary: str,
    why: str = ""
) -> None:
    """Generate and store/update embedding for an issue.
    
    Creates a combined text from title + summary + why, generates embedding,
    and upserts into issue_embeddings table. Called when creating or merging issues.
    
    Args:
        issue_id: Issue identifier
        title: Issue title
        summary: Issue summary
        why: Why this issue matters (optional)
    """
    # Combine into single text for embedding
    combined_text = f"{title}\n\n{summary}"
    if why:
        combined_text += f"\n\n{why}"
    
    # Generate embedding
    embedding = generate_embedding(combined_text)
    embedding_str = "[" + ",".join(str(x) for x in embedding) + "]"
    
    # Upsert (ON CONFLICT DO UPDATE for re-embedding after merges)
    sql = """
        INSERT INTO issue_embeddings (issue_id, embedding, created_at)
        VALUES (:issue_id, CAST(:embedding AS vector), now())
        ON CONFLICT (issue_id) DO UPDATE
        SET embedding = EXCLUDED.embedding,
            created_at = now()
    """
    
    with get_session() as session:
        session.execute(text(sql), {"issue_id": issue_id, "embedding": embedding_str})
        session.commit()


def search_similar_reports(
    query: str,
    top_k: int = 5
) -> list[dict]:
    """Search past discovery reports for semantic memory recall.
    
    Discovery agent can query "have I tried something like this before?" and
    learn from past successes/failures, effective queries, and tag patterns.
    
    Args:
        query: Natural language query (e.g., topic, instruction, or strategy)
        top_k: Number of relevant report chunks to return (default 5)
        
    Returns:
        List of dicts with keys: report_id, topic, instruction, findings,
        chunk_text, similarity
    """
    # Generate embedding for query
    query_embedding = generate_embedding(query)
    embedding_str = "[" + ",".join(str(x) for x in query_embedding) + "]"
    
    # Query report chunks and join to parent report metadata
    sql = """
        SELECT 
            drc.report_id,
            dr.topic,
            dr.instruction,
            dr.findings,
            drc.chunk_text,
            1 - (drc.embedding <=> CAST(:embedding AS vector)) AS similarity
        FROM discovery_report_chunks drc
        JOIN discovery_reports dr ON drc.report_id = dr.id
        ORDER BY drc.embedding <=> CAST(:embedding AS vector)
        LIMIT :top_k
    """
    
    params = {"embedding": embedding_str, "top_k": top_k}
    
    with get_session() as session:
        result = session.execute(text(sql), params)
        rows = result.fetchall()
        
        return [
            {
                "report_id": int(row[0]),
                "topic": row[1],
                "instruction": row[2],
                "findings": row[3],  # JSONB is returned as dict
                "chunk_text": row[4],
                "similarity": float(row[5]),
            }
            for row in rows
        ]


def search_similar_content(
    query: str,
    top_k: int = 5,
    component_types: list[str] | None = None,
    exclude_issue_id: str | None = None
) -> list[dict]:
    """Search for content similar to the query using vector similarity.
    
    Args:
        query: Natural language search query
        top_k: Number of results to return (default 5)
        component_types: Optional filter for specific component types
        exclude_issue_id: Optional issue ID to exclude from results
        
    Returns:
        List of dicts with keys: issue_id, component_type, version, chunk_index,
        chunk_text, similarity (0-1, higher is more similar)
    """
    # Generate embedding for query
    query_embedding = generate_embedding(query)
    
    # Convert to PostgreSQL array format
    embedding_str = "[" + ",".join(str(x) for x in query_embedding) + "]"
    
    # Build WHERE clause filters
    where_clauses = []
    params = {"embedding": embedding_str, "top_k": top_k}
    
    if component_types:
        where_clauses.append("component_type = ANY(:component_types)")
        params["component_types"] = component_types
        
    if exclude_issue_id:
        where_clauses.append("issue_id != :exclude_issue_id")
        params["exclude_issue_id"] = exclude_issue_id
    
    where_sql = "WHERE " + " AND ".join(where_clauses) if where_clauses else ""
    
    # Query using cosine similarity (1 - cosine_distance)
    sql = f"""
        SELECT 
            issue_id,
            component_type,
            version,
            chunk_index,
            chunk_text,
            1 - (embedding <=> CAST(:embedding AS vector)) AS similarity
        FROM component_embeddings
        {where_sql}
        ORDER BY embedding <=> CAST(:embedding AS vector)
        LIMIT :top_k
    """
    
    with get_session() as session:
        result = session.execute(text(sql), params)
        rows = result.fetchall()
        
        return [
            {
                "issue_id": row[0],
                "component_type": row[1],
                "version": row[2],
                "chunk_index": row[3],
                "chunk_text": row[4],
                "similarity": float(row[5]),
            }
            for row in rows
        ]


def search_within_issue(
    issue_id: str,
    query: str,
    top_k: int = 3,
    component_types: list[str] | None = None
) -> list[dict]:
    """Search for content within a specific issue using vector similarity.
    
    Useful for finding relevant context within an issue's knowledge base.
    
    Args:
        issue_id: Issue to search within
        query: Natural language search query
        top_k: Number of results to return (default 3)
        component_types: Optional filter for specific component types
        
    Returns:
        List of dicts with keys: component_type, version, chunk_index,
        chunk_text, similarity
    """
    # Generate embedding for query
    query_embedding = generate_embedding(query)
    
    # Convert to PostgreSQL array format
    embedding_str = "[" + ",".join(str(x) for x in query_embedding) + "]"
    
    # Build WHERE clause
    where_sql = "WHERE issue_id = :issue_id"
    params = {"issue_id": issue_id, "embedding": embedding_str, "top_k": top_k}
    
    if component_types:
        where_sql += " AND component_type = ANY(:component_types)"
        params["component_types"] = component_types
    
    sql = f"""
        SELECT 
            component_type,
            version,
            chunk_index,
            chunk_text,
            1 - (embedding <=> CAST(:embedding AS vector)) AS similarity
        FROM component_embeddings
        {where_sql}
        ORDER BY embedding <=> CAST(:embedding AS vector)
        LIMIT :top_k
    """
    
    with get_session() as session:
        result = session.execute(text(sql), params)
        rows = result.fetchall()
        
        return [
            {
                "component_type": row[0],
                "version": row[1],
                "chunk_index": row[2],
                "chunk_text": row[3],
                "similarity": float(row[4]),
            }
            for row in rows
        ]
