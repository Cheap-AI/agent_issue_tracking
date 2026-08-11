"""Vector similarity search using pgvector."""
from sqlalchemy import text

from backend.core.db import get_session
from backend.services.embedding import generate_embedding


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
            1 - (embedding <=> :embedding::vector) AS similarity
        FROM component_embeddings
        {where_sql}
        ORDER BY embedding <=> :embedding::vector
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
            1 - (embedding <=> :embedding::vector) AS similarity
        FROM component_embeddings
        {where_sql}
        ORDER BY embedding <=> :embedding::vector
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
