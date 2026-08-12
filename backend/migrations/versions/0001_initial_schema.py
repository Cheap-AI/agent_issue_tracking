"""initial schema: issues, components, global_docs

Revision ID: 0001
Revises:
Create Date: 2026-07-24

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = "0001"
down_revision: Union[str, Sequence[str], None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.execute("CREATE SEQUENCE IF NOT EXISTS issue_id_seq START WITH 1")

    op.create_table(
        "issues",
        sa.Column("id", sa.String(), primary_key=True),
        sa.Column("title", sa.Text(), nullable=False),
        sa.Column("summary", sa.Text(), nullable=False, server_default=""),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
    )

    op.create_table(
        "components",
        sa.Column("id", sa.BigInteger(), primary_key=True, autoincrement=True),
        sa.Column("issue_id", sa.String(), sa.ForeignKey("issues.id", ondelete="CASCADE"), nullable=False),
        sa.Column("component_type", sa.Text(), nullable=False),
        sa.Column("version", sa.Integer(), nullable=False),
        sa.Column("content", sa.Text(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.UniqueConstraint("issue_id", "component_type", "version", name="uq_component_version"),
        sa.CheckConstraint(
            "component_type IN ('research', 'summary', 'timeline', 'sources', 'questions')",
            name="ck_component_type",
        ),
    )

    op.create_table(
        "global_docs",
        sa.Column("name", sa.String(), primary_key=True),
        sa.Column("content", sa.Text(), nullable=False, server_default=""),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_table("global_docs")
    op.drop_table("components")
    op.drop_table("issues")
    op.execute("DROP SEQUENCE IF EXISTS issue_id_seq")
