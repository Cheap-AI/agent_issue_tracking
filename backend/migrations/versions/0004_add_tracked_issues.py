"""add tracked_issues table and ranking config

Revision ID: 0004
Revises: 0003
Create Date: 2026-08-11

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = "0004"
down_revision: Union[str, Sequence[str], None] = "0003"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Add tracked_issues table for curation leaderboard."""
    op.create_table(
        "tracked_issues",
        sa.Column("id", sa.BigInteger(), primary_key=True, autoincrement=True),
        sa.Column("issue_id", sa.String(), sa.ForeignKey("issues.id", ondelete="CASCADE"), nullable=False, unique=True),
        sa.Column("dimension_scores", sa.JSON(), nullable=False),  # {"severity": 8, "impact": 7, "scale": 9, "recency": 6}
        sa.Column("overall_score", sa.Float(), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("first_seen_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("last_updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now(), onupdate=sa.func.now()),
    )

    # Index for querying active tracked issues sorted by score
    op.create_index("idx_tracked_issues_active_score", "tracked_issues", ["is_active", "overall_score"])

    # Seed ranking configuration in global_docs
    op.execute("""
        INSERT INTO global_docs (name, content) 
        VALUES (
            'ranking_config',
            '{"top_n": 50, "formula": "mean", "dimensions": ["severity", "impact", "scale", "recency"], "weights": {"severity": 1.0, "impact": 1.0, "scale": 1.0, "recency": 1.0}}'
        )
        ON CONFLICT (name) DO NOTHING;
    """)


def downgrade() -> None:
    """Remove tracked_issues table and ranking config."""
    op.execute("DELETE FROM global_docs WHERE name = 'ranking_config';")
    op.drop_index("idx_tracked_issues_active_score")
    op.drop_table("tracked_issues")
