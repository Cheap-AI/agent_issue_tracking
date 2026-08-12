from fastapi import BackgroundTasks

from backend.core import versioning
from backend.core.db import get_session
from backend.core.issue import COMPONENTS
from backend.models.db_models import Component, ComponentEmbedding
from backend.services.chunking import chunk_text
from backend.services.embedding import generate_embeddings_batch


def update_component(
    issue_id: str,
    component: str,
    new_content: str,
    background_tasks: BackgroundTasks | None = None,
) -> int:
    """Save new_content as the next immutable version of a knowledge component
    (research/summary/timeline/sources/questions). Returns the new version number.
    
    Args:
        issue_id: Issue identifier
        component: Component type (research/summary/timeline/sources/questions)
        new_content: Content to save
        background_tasks: FastAPI BackgroundTasks for async embedding generation.
                         If None, embeddings are generated synchronously (useful for testing).
    
    Returns:
        Version number of the saved component
        
    Note:
        When background_tasks is provided, the function returns immediately and embeddings
        are generated in background using FastAPI's thread pool. When None, it blocks until
        embeddings are done (useful for scripts and testing).
    """
    if component not in COMPONENTS:
        raise ValueError(f"Unknown component '{component}', expected one of {COMPONENTS}")
    
    version = versioning.save_version(issue_id, component, new_content)
    
    if background_tasks:
        # Queue background task - FastAPI manages the thread pool
        background_tasks.add_task(
            _generate_embeddings_for_component,
            issue_id,
            component,
            version,
            new_content
        )
    else:
        # Synchronous mode for testing/scripts
        _generate_embeddings_for_component(issue_id, component, version, new_content)
    
    return version


def _generate_embeddings_for_component(
    issue_id: str, component_type: str, version: int, content: str
) -> None:
    """Generate and store embeddings for a component version.
    
    Chunks the content and generates embeddings for all chunks in a single batch API call.
    """
    # Chunk the content
    chunks = chunk_text(content)
    
    if not chunks:
        return  # No content to embed
    
    # Generate embeddings in batch (more efficient than one-by-one)
    embeddings = generate_embeddings_batch(chunks)
    
    # Store embeddings in database
    with get_session() as session:
        # Get the component ID
        component_obj = session.query(Component).filter_by(
            issue_id=issue_id,
            component_type=component_type,
            version=version
        ).first()
        
        if not component_obj:
            raise ValueError(f"Component not found: {issue_id}/{component_type}/v{version}")
        
        # Create embedding records
        for chunk_index, (chunk, embedding) in enumerate(zip(chunks, embeddings)):
            # Convert embedding list to PostgreSQL array string format
            embedding_str = "[" + ",".join(str(x) for x in embedding) + "]"
            
            emb_obj = ComponentEmbedding(
                component_id=component_obj.id,
                issue_id=issue_id,
                component_type=component_type,
                version=version,
                chunk_index=chunk_index,
                chunk_text=chunk,
                embedding=embedding_str
            )
            session.add(emb_obj)
        
        session.commit()


def read_current(issue_id: str, component: str) -> tuple[int, str] | None:
    """Return (version_number, content) for the current (latest) version of a component, or None."""
    return versioning.get_current_version(issue_id, component)


def read_history(issue_id: str, component: str) -> list[int]:
    """Return all version numbers stored for a component, ascending."""
    return versioning.list_versions(issue_id, component)
