"""add entry_type to alarm_event

Revision ID: 4f5a1b2c3d4e
Revises: 2d4e9f0a1c3b
Create Date: 2026-05-14 13:30:00.000000

"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "4f5a1b2c3d4e"
down_revision: str | Sequence[str] | None = "2d4e9f0a1c3b"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Upgrade schema."""
    op.add_column(
        "alarmevent",
        sa.Column("entry_type", sa.String(), nullable=False, server_default="alarm"),
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_column("alarmevent", "entry_type")
