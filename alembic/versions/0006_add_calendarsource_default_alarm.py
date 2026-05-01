"""add_calendarsource_default_alarm

Revision ID: 0006
Revises: 0005
Create Date: 2026-05-01

Adds default_alarm_for_all_events column to calendarsource table.
Note: this migration's changes were previously applied by the project's
`migrate_database()` helper using raw sqlite3 operations; the Alembic
revision is retained here for traceability.
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "0006"
down_revision: str | Sequence[str] | None = "0005"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    with op.batch_alter_table("calendarsource") as batch_op:
        batch_op.add_column(
            sa.Column(
                "default_alarm_for_all_events",
                sa.Boolean(),
                nullable=False,
                server_default=sa.text("0"),
            )
        )


def downgrade() -> None:
    with op.batch_alter_table("calendarsource") as batch_op:
        batch_op.drop_column("default_alarm_for_all_events")
