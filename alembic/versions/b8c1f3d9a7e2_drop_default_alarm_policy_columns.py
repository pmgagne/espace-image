"""drop default alarm policy columns

Revision ID: b8c1f3d9a7e2
Revises: 4f5a1b2c3d4e
Create Date: 2026-05-14 23:10:00.000000

"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "b8c1f3d9a7e2"
down_revision: str | Sequence[str] | None = "4f5a1b2c3d4e"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def _has_column(table: str, column: str) -> bool:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    return column in {c["name"] for c in inspector.get_columns(table)}


def upgrade() -> None:
    """Upgrade schema."""
    if _has_column("calendarsource", "default_alarm_for_all_events"):
        op.drop_column("calendarsource", "default_alarm_for_all_events")

    if _has_column("appsettings", "default_alarm_for_all_events"):
        op.drop_column("appsettings", "default_alarm_for_all_events")


def downgrade() -> None:
    """Downgrade schema."""
    if not _has_column("calendarsource", "default_alarm_for_all_events"):
        op.add_column(
            "calendarsource",
            sa.Column(
                "default_alarm_for_all_events",
                sa.Boolean(),
                nullable=False,
                server_default=sa.text("0"),
            ),
        )

    if not _has_column("appsettings", "default_alarm_for_all_events"):
        op.add_column(
            "appsettings",
            sa.Column(
                "default_alarm_for_all_events",
                sa.Boolean(),
                nullable=False,
                server_default=sa.text("0"),
            ),
        )
