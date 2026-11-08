"""split issue tags into geography / topics / affected_groups

Revision ID: 0012
Revises: 0011
Create Date: 2026-11-08

"""
import json
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "0012"
down_revision: Union[str, Sequence[str], None] = "0011"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

# Frozen copy: migrations must not depend on app code that may change later.
_GEOGRAPHY = {
    "global", "africa", "asia", "europe", "latin-america", "middle-east",
    "north-america", "south-america", "oceania", "caribbean",
    "afghanistan", "canada", "north-korea", "u.s.", "u.k.", "us", "uk", "usa",
    "china", "russia", "india", "japan", "korea", "south-korea", "ukraine",
    "israel", "iran", "mexico", "brazil", "australia", "germany", "france",
}


def upgrade() -> None:
    for column in ("geography", "topics", "affected_groups"):
        op.add_column("issues", sa.Column(column, sa.JSON(), nullable=True))

    bind = op.get_bind()
    rows = bind.execute(sa.text("SELECT id, tags FROM issues")).fetchall()
    for issue_id, tags in rows:
        if isinstance(tags, str):
            tags = json.loads(tags)
        geography, topics = [], []
        for tag in tags or []:
            key = str(tag).strip().lower().replace(" ", "-")
            (geography if key in _GEOGRAPHY else topics).append(tag)
        bind.execute(
            sa.text(
                "UPDATE issues SET geography = CAST(:g AS json), topics = CAST(:t AS json), "
                "affected_groups = CAST('[]' AS json) WHERE id = :id"
            ),
            {"g": json.dumps(geography), "t": json.dumps(topics), "id": issue_id},
        )

    for column in ("geography", "topics", "affected_groups"):
        op.alter_column("issues", column, nullable=False)


def downgrade() -> None:
    for column in ("affected_groups", "topics", "geography"):
        op.drop_column("issues", column)
