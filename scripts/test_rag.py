"""Test RAG components: chunking, embeddings, and vector search."""
import sys
import os

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from backend.services.chunking import chunk_text
from backend.services.embedding import generate_embedding, generate_embeddings_batch
from backend.services.vector_search import search_similar_content
from backend.core.knowledge import update_component
from backend.core.issue import create_issue


def test_chunking():
    """Test text chunking."""
    print("=== Test 1: Chunking ===")
    
    # Short text (should be 1 chunk)
    short = "This is a short text."
    chunks = chunk_text(short, chunk_size=512, overlap=50)
    print(f"Short text chunks: {len(chunks)}")
    assert len(chunks) == 1, "Short text should be 1 chunk"
    
    # Long text (should be multiple chunks)
    long = " ".join(["This is sentence number " + str(i) + "." for i in range(200)])
    chunks = chunk_text(long, chunk_size=100, overlap=20)
    print(f"Long text chunks: {len(chunks)}")
    assert len(chunks) > 1, "Long text should be multiple chunks"
    
    print("✓ Chunking works\n")


def test_embeddings():
    """Test embedding generation."""
    print("=== Test 2: Embeddings ===")
    
    # Single embedding
    text = "OpenAI released GPT-4 in March 2023."
    embedding = generate_embedding(text)
    print(f"Single embedding dimensions: {len(embedding)}")
    assert len(embedding) == 1536, "Should be 1536 dimensions"
    
    # Batch embeddings
    texts = [
        "Python is a programming language.",
        "FastAPI is a web framework.",
        "PostgreSQL is a database."
    ]
    embeddings = generate_embeddings_batch(texts)
    print(f"Batch embeddings count: {len(embeddings)}")
    assert len(embeddings) == 3, "Should have 3 embeddings"
    assert all(len(e) == 1536 for e in embeddings), "All should be 1536 dimensions"
    
    print("✓ Embeddings work\n")


def test_vector_search():
    """Test vector search with real data."""
    print("=== Test 3: Vector Search ===")
    
    # Create a test issue
    issue = create_issue(
        title="Test RAG Issue",
        summary="Testing the RAG system with vector search"
    )
    issue_id = issue["id"]
    print(f"Created test issue: {issue_id}")
    
    # Add research content
    research_content = """
    Vector search enables semantic similarity matching. It works by converting text into 
    high-dimensional embeddings and using cosine similarity to find related content.
    
    OpenAI's text-embedding-3-small model produces 1536-dimensional vectors that capture
    semantic meaning. This allows finding conceptually similar text even when exact keywords differ.
    
    Applications include RAG (Retrieval Augmented Generation), recommendation systems,
    and semantic search engines.
    """
    
    version = update_component(issue_id, "research", research_content)
    print(f"Added research content (v{version})")
    
    # Wait a moment for embeddings to be generated
    import time
    time.sleep(2)
    
    # Search for related content
    query = "What is semantic search and how does it work?"
    results = search_similar_content(query, top_k=3)
    
    print(f"Search results for: '{query}'")
    print(f"Found {len(results)} results")
    
    if results:
        for i, result in enumerate(results, 1):
            print(f"\n  Result {i}:")
            print(f"    Issue: {result['issue_id']}")
            print(f"    Component: {result['component_type']} v{result['version']}")
            print(f"    Similarity: {result['similarity']:.3f}")
            print(f"    Text: {result['chunk_text'][:100]}...")
    
    print("\n✓ Vector search works\n")


if __name__ == "__main__":
    try:
        test_chunking()
        test_embeddings()
        test_vector_search()
        
        print("=" * 50)
        print("✓ All RAG components working!")
        print("=" * 50)
        
    except Exception as e:
        print(f"\n✗ Test failed: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
