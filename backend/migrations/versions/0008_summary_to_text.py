"""Change discovery_reports.summary from JSON to TEXT

Revision ID: 0008
Revises: 0007
Create Date: 2026-08-12
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic
revision = '0008'
down_revision = '0007'
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Change summary column from JSONB to TEXT for narrative summaries."""
    # Drop the JSON constraint and change column type
    op.alter_column(
        'discovery_reports',
        'summary',
        type_=sa.Text(),
        existing_type=postgresql.JSON(astext_type=sa.Text()),
        existing_nullable=False,
        existing_server_default='{}',
        server_default=''
    )


def downgrade() -> None:
    """Revert summary column back to JSONB."""
    op.alter_column(
        'discovery_reports',
        'summary',
        type_=postgresql.JSON(astext_type=sa.Text()),
        existing_type=sa.Text(),
        existing_nullable=False,
        existing_server_default='',
        server_default='{}'
    )
