"""add embeddings table for RAG

Revision ID: 0002
Revises: 0001
Create Date: 2026-08-11

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = "0002"
down_revision: Union[str, Sequence[str], None] = "0001"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Add component_embeddings table for vector similarity search."""
    # Create table with embedding column as vector type using raw SQL
    op.execute("""
        CREATE TABLE component_embeddings (
            id BIGSERIAL PRIMARY KEY,
            component_id BIGINT NOT NULL REFERENCES components(id) ON DELETE CASCADE,
            issue_id VARCHAR NOT NULL REFERENCES issues(id) ON DELETE CASCADE,
            component_type TEXT NOT NULL,
            version INTEGER NOT NULL,
            chunk_index INTEGER NOT NULL,
            chunk_text TEXT NOT NULL,
            embedding vector(1536) NOT NULL,
            created_at TIMESTAMPTZ NOT NULL DEFAULT now()
        );
    """)

    # Create ivfflat index for fast cosine similarity search
    op.execute("""
        CREATE INDEX component_embeddings_embedding_idx 
        ON component_embeddings 
        USING ivfflat (embedding vector_cosine_ops)
        WITH (lists = 100);
    """)


def downgrade() -> None:
    """Remove component_embeddings table."""
    op.drop_table("component_embeddings")
