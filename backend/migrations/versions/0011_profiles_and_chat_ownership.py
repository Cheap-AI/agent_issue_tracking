"""Add profiles (users + roles) and chat_sessions.user_id

Revision ID: 0011
Revises: 0010
Create Date: 2026-11-03

"""
from typing import Sequence, Union

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "0011"
down_revision: Union[str, Sequence[str], None] = "0010"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # id mirrors Supabase auth.users.id (no FK so migrations also work on a plain Postgres).
    op.execute("""
        CREATE TABLE profiles (
            id UUID PRIMARY KEY,
            email TEXT,
            role TEXT NOT NULL DEFAULT 'member' CHECK (role IN ('admin', 'member')),
            created_at TIMESTAMPTZ NOT NULL DEFAULT now()
        );
    """)

    # Nullable: pre-auth sessions have no owner and become inaccessible.
    op.execute("""
        ALTER TABLE chat_sessions
        ADD COLUMN user_id UUID REFERENCES profiles(id) ON DELETE CASCADE;
    """)
    op.execute("CREATE INDEX chat_sessions_user_id_idx ON chat_sessions(user_id);")


def downgrade() -> None:
    op.execute("DROP INDEX IF EXISTS chat_sessions_user_id_idx;")
    op.execute("ALTER TABLE chat_sessions DROP COLUMN IF EXISTS user_id;")
    op.execute("DROP TABLE IF EXISTS profiles;")
