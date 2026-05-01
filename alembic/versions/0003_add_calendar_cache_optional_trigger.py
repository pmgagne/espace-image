"""add_calendar_cache_optional_trigger

Revision ID: 0003
Revises: 0002
Create Date: 2026-05-01

Adds optional_trigger column and index to calendar_event_cache table.
Previously applied via raw sqlite3 in migrate_database().
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "0003"
down_revision: str | Sequence[str] | None = "0002"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    with op.batch_alter_table("calendar_event_cache") as batch_op:
        batch_op.add_column(
            sa.Column(
                "optional_trigger",
                sa.Boolean(),
                nullable=False,
                server_default=sa.text("0"),
            )
        )
        batch_op.create_index(
            "ix_calendar_event_cache_optional_trigger",
            ["optional_trigger"],
        )


def downgrade() -> None:
    with op.batch_alter_table("calendar_event_cache") as batch_op:
        batch_op.drop_index("ix_calendar_event_cache_optional_trigger")
        batch_op.drop_column("optional_trigger")
