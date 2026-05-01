"""add_appsettings_default_alarm

Revision ID: 0001
Revises: f823da104bcb
Create Date: 2026-05-01

Adds default_alarm_for_all_events column to appsettings table.
Previously applied via raw sqlite3 in migrate_database().
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "0001"
down_revision: str | Sequence[str] | None = "f823da104bcb"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    with op.batch_alter_table("appsettings") as batch_op:
        batch_op.add_column(
            sa.Column(
                "default_alarm_for_all_events",
                sa.Boolean(),
                nullable=False,
                server_default=sa.text("0"),
            )
        )


def downgrade() -> None:
    with op.batch_alter_table("appsettings") as batch_op:
        batch_op.drop_column("default_alarm_for_all_events")
