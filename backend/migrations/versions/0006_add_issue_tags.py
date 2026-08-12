"""add tags column to issues

Revision ID: 0006
Revises: 0005
Create Date: 2026-08-11

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = "0006"
down_revision: Union[str, Sequence[str], None] = "0005"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Add tags array column to issues."""
    op.add_column(
        "issues",
        sa.Column("tags", sa.JSON(), nullable=True),
    )
    # Set default empty array for existing rows
    op.execute("UPDATE issues SET tags = '[]' WHERE tags IS NULL")


def downgrade() -> None:
    """Remove tags column from issues."""
    op.drop_column("issues", "tags")
