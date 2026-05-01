"""add_calendar_cache_event_tz

Revision ID: 0004
Revises: 0003
Create Date: 2026-05-01

Adds event_tz column and index to calendar_event_cache table.
Previously applied via raw sqlite3 in migrate_database().
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "0004"
down_revision: str | Sequence[str] | None = "0003"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    with op.batch_alter_table("calendar_event_cache") as batch_op:
        batch_op.add_column(sa.Column("event_tz", sa.Text(), nullable=True))
        batch_op.create_index(
            "ix_calendar_event_cache_event_tz",
            ["event_tz"],
        )


def downgrade() -> None:
    with op.batch_alter_table("calendar_event_cache") as batch_op:
        batch_op.drop_index("ix_calendar_event_cache_event_tz")
        batch_op.drop_column("event_tz")
