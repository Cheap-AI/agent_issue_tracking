"""add events table for timeline

Revision ID: 0003
Revises: 0002
Create Date: 2026-08-11

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = "0003"
down_revision: Union[str, Sequence[str], None] = "0002"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Add events table for discrete timeline events."""
    op.create_table(
        "events",
        sa.Column("id", sa.BigInteger(), primary_key=True, autoincrement=True),
        sa.Column("issue_id", sa.String(), sa.ForeignKey("issues.id", ondelete="CASCADE"), nullable=False),
        sa.Column("event_date", sa.Date(), nullable=True),  # When event happened (nullable if unknown)
        sa.Column("discovered_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("title", sa.Text(), nullable=False),
        sa.Column("description", sa.Text(), nullable=False, server_default=""),
        sa.Column("source_urls", sa.JSON(), nullable=False, server_default="[]"),
        sa.Column("component_id", sa.BigInteger(), sa.ForeignKey("components.id", ondelete="SET NULL"), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
    )

    # Index for querying events by issue and date
    op.create_index("idx_events_issue_date", "events", ["issue_id", "event_date"])


def downgrade() -> None:
    """Remove events table."""
    op.drop_index("idx_events_issue_date")
    op.drop_table("events")
