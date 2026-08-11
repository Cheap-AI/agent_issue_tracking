"""Embedding generation service using OpenAI."""
import os

from openai import OpenAI


# Initialize OpenAI client
client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))


def generate_embedding(text: str) -> list[float]:
    """Generate embedding vector for text using OpenAI text-embedding-3-small.
    
    Args:
        text: Text to embed
        
    Returns:
        1536-dimensional embedding vector
        
    Raises:
        OpenAI API errors if request fails
    """
    response = client.embeddings.create(
        model="text-embedding-3-small",
        input=text,
        encoding_format="float"
    )
    
    return response.data[0].embedding


def generate_embeddings_batch(texts: list[str]) -> list[list[float]]:
    """Generate embeddings for multiple texts in a single API call.
    
    More efficient than calling generate_embedding() multiple times.
    
    Args:
        texts: List of texts to embed
        
    Returns:
        List of 1536-dimensional embedding vectors
        
    Raises:
        OpenAI API errors if request fails
    """
    if not texts:
        return []
    
    response = client.embeddings.create(
        model="text-embedding-3-small",
        input=texts,
        encoding_format="float"
    )
    
    # Response data is in order matching input texts
    return [item.embedding for item in response.data]
