"""Add issues.target_year/target_month and versioned monthly_reports tables

Revision ID: 0009
Revises: 0008
Create Date: 2026-10-17

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = "0009"
down_revision: Union[str, Sequence[str], None] = "0008"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Add nullable target_year/target_month to issues; add monthly_reports + chunks tables."""

    op.add_column("issues", sa.Column("target_year", sa.Integer(), nullable=True))
    op.add_column("issues", sa.Column("target_month", sa.Integer(), nullable=True))
    op.create_check_constraint(
        "ck_issues_target_month_range",
        "issues",
        "target_month IS NULL OR (target_month BETWEEN 1 AND 12)",
    )

    op.execute("""
        CREATE TABLE monthly_reports (
            id BIGSERIAL PRIMARY KEY,
            year INTEGER NOT NULL,
            month INTEGER NOT NULL CHECK (month BETWEEN 1 AND 12),
            version INTEGER NOT NULL,
            overview TEXT NOT NULL DEFAULT '',
            big_picture TEXT NOT NULL DEFAULT '',
            metadata JSONB NOT NULL DEFAULT '{}',
            created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
            UNIQUE (year, month, version)
        );
    """)

    op.execute("""
        CREATE INDEX monthly_reports_year_month_idx
        ON monthly_reports(year, month, version DESC);
    """)

    op.execute("""
        CREATE TABLE monthly_report_chunks (
            id BIGSERIAL PRIMARY KEY,
            monthly_report_id BIGINT NOT NULL REFERENCES monthly_reports(id) ON DELETE CASCADE,
            chunk_index INTEGER NOT NULL,
            chunk_text TEXT NOT NULL,
            embedding vector(1536) NOT NULL,
            created_at TIMESTAMPTZ NOT NULL DEFAULT now()
        );
    """)

    op.execute("""
        CREATE INDEX monthly_report_chunks_embedding_idx
        ON monthly_report_chunks
        USING ivfflat (embedding vector_cosine_ops)
        WITH (lists = 100);
    """)

    op.execute("""
        CREATE INDEX monthly_report_chunks_report_id_idx
        ON monthly_report_chunks(monthly_report_id);
    """)


def downgrade() -> None:
    op.execute("DROP TABLE IF EXISTS monthly_report_chunks;")
    op.execute("DROP TABLE IF EXISTS monthly_reports;")
    op.drop_constraint("ck_issues_target_month_range", "issues", type_="check")
    op.drop_column("issues", "target_month")
    op.drop_column("issues", "target_year")
