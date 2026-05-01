"""add_calendar_cache_trigger_time

Revision ID: 0002
Revises: 0001
Create Date: 2026-05-01

Adds trigger_time column and index to calendar_event_cache table.
Previously applied via raw sqlite3 in migrate_database().
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "0002"
down_revision: str | Sequence[str] | None = "0001"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    with op.batch_alter_table("calendar_event_cache") as batch_op:
        batch_op.add_column(sa.Column("trigger_time", sa.DateTime(), nullable=True))
        batch_op.create_index(
            "ix_calendar_event_cache_trigger_time",
            ["trigger_time"],
        )


def downgrade() -> None:
    with op.batch_alter_table("calendar_event_cache") as batch_op:
        batch_op.drop_index("ix_calendar_event_cache_trigger_time")
        batch_op.drop_column("trigger_time")
