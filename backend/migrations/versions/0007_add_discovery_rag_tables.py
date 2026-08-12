"""add discovery RAG tables

Revision ID: 0007
Revises: 0006
Create Date: 2026-08-11

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = "0007"
down_revision: Union[str, Sequence[str], None] = "0006"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Add issue_embeddings, discovery_reports, and discovery_report_chunks tables."""
    
    # 1. issue_embeddings - one row per issue for fast deduplication
    op.execute("""
        CREATE TABLE issue_embeddings (
            id BIGSERIAL PRIMARY KEY,
            issue_id VARCHAR NOT NULL UNIQUE REFERENCES issues(id) ON DELETE CASCADE,
            embedding vector(1536) NOT NULL,
            created_at TIMESTAMPTZ NOT NULL DEFAULT now()
        );
    """)
    
    # Create ivfflat index for fast cosine similarity search
    op.execute("""
        CREATE INDEX issue_embeddings_embedding_idx 
        ON issue_embeddings 
        USING ivfflat (embedding vector_cosine_ops)
        WITH (lists = 100);
    """)
    
    # 2. discovery_reports - replaces JSON file storage
    op.execute("""
        CREATE TABLE discovery_reports (
            id BIGSERIAL PRIMARY KEY,
            topic TEXT NOT NULL,
            instruction TEXT NOT NULL,
            target_count INTEGER NOT NULL,
            actual_created INTEGER NOT NULL,
            iterations INTEGER NOT NULL,
            review_mode BOOLEAN NOT NULL DEFAULT false,
            api_usage JSONB NOT NULL DEFAULT '{}',
            findings JSONB NOT NULL DEFAULT '[]',
            proposed_duplicates JSONB NOT NULL DEFAULT '[]',
            summary JSONB NOT NULL DEFAULT '{}',
            created_at TIMESTAMPTZ NOT NULL DEFAULT now()
        );
    """)
    
    # Index for querying recent reports and daily counts
    op.execute("""
        CREATE INDEX discovery_reports_created_at_idx 
        ON discovery_reports(created_at DESC);
    """)
    
    # 3. discovery_report_chunks - for semantic memory recall
    op.execute("""
        CREATE TABLE discovery_report_chunks (
            id BIGSERIAL PRIMARY KEY,
            report_id BIGINT NOT NULL REFERENCES discovery_reports(id) ON DELETE CASCADE,
            chunk_index INTEGER NOT NULL,
            chunk_text TEXT NOT NULL,
            embedding vector(1536) NOT NULL,
            created_at TIMESTAMPTZ NOT NULL DEFAULT now()
        );
    """)
    
    # Create ivfflat index for semantic search
    op.execute("""
        CREATE INDEX discovery_report_chunks_embedding_idx 
        ON discovery_report_chunks 
        USING ivfflat (embedding vector_cosine_ops)
        WITH (lists = 100);
    """)
    
    # Index for joining back to reports
    op.execute("""
        CREATE INDEX discovery_report_chunks_report_id_idx 
        ON discovery_report_chunks(report_id);
    """)


def downgrade() -> None:
    """Remove discovery RAG tables."""
    op.drop_table("discovery_report_chunks")
    op.drop_table("discovery_reports")
    op.drop_table("issue_embeddings")
