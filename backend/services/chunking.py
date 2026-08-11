"""Text chunking utilities for RAG system.

Uses tiktoken to count tokens and split text into overlapping chunks.

Look into Anthropic's contextual enrichment and Parent-cild retrieval
"""
import tiktoken


def chunk_text(text: str, chunk_size: int = 512, overlap: int = 50) -> list[str]:
    """Split text into overlapping chunks based on token count.
    
    Args:
        text: The text to chunk
        chunk_size: Maximum tokens per chunk (default 512)
        overlap: Number of overlapping tokens between chunks (default 50)
        
    Returns:
        List of text chunks
    """
    if not text.strip():
        return []
    
    # Use cl100k_base encoding (same as gpt-4, gpt-3.5-turbo)
    encoding = tiktoken.get_encoding("cl100k_base")
    
    # Encode the full text
    tokens = encoding.encode(text)
    
    # If text fits in one chunk, return it
    if len(tokens) <= chunk_size:
        return [text]
    
    chunks = []
    start = 0
    
    while start < len(tokens):
        # Get chunk_size tokens starting from start
        end = min(start + chunk_size, len(tokens))
        chunk_tokens = tokens[start:end]
        
        # Decode back to text
        chunk_text = encoding.decode(chunk_tokens)
        chunks.append(chunk_text)
        
        # Move to next chunk with overlap
        # If we're at the end, break to avoid infinite loop
        if end >= len(tokens):
            break
            
        start = end - overlap
    
    return chunks
