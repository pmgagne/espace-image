"""add_calendar_cache_all_day

Revision ID: 0005
Revises: 0004
Create Date: 2026-05-01

Adds all_day column and index to calendar_event_cache table.
Note: this migration's changes were previously applied by the project's
`migrate_database()` helper using raw sqlite3 operations; the Alembic
revision is retained here for traceability.
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "0005"
down_revision: str | Sequence[str] | None = "0004"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    with op.batch_alter_table("calendar_event_cache") as batch_op:
        batch_op.add_column(
            sa.Column(
                "all_day",
                sa.Boolean(),
                nullable=False,
                server_default=sa.text("0"),
            )
        )
        batch_op.create_index(
            "ix_calendar_event_cache_all_day",
            ["all_day"],
        )


def downgrade() -> None:
    with op.batch_alter_table("calendar_event_cache") as batch_op:
        batch_op.drop_index("ix_calendar_event_cache_all_day")
        batch_op.drop_column("all_day")
