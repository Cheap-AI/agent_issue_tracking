"""add why column to issues

Revision ID: 0005
Revises: 0004
Create Date: 2026-08-11

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = "0005"
down_revision: Union[str, Sequence[str], None] = "0004"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Add why explanation column to issues."""
    op.add_column(
        "issues",
        sa.Column("why", sa.Text(), nullable=False, server_default=""),
    )


def downgrade() -> None:
    """Remove why explanation column from issues."""
    op.drop_column("issues", "why")
