"""add origin (longevity) columns to issues

Revision ID: 0013
Revises: 0012
Create Date: 2026-11-08

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "0013"
down_revision: Union[str, Sequence[str], None] = "0012"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """All nullable: NULL means "not estimated yet". Filled by backend/services/origin.py."""
    op.add_column("issues", sa.Column("origin_year", sa.Integer(), nullable=True))
    op.add_column("issues", sa.Column("origin_precision", sa.Text(), nullable=True))
    op.add_column("issues", sa.Column("origin_confidence", sa.Text(), nullable=True))
    op.add_column("issues", sa.Column("origin_basis", sa.Text(), nullable=True))


def downgrade() -> None:
    for column in ("origin_basis", "origin_confidence", "origin_precision", "origin_year"):
        op.drop_column("issues", column)
