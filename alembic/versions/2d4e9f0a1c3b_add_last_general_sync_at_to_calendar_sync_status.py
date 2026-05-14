"""add last_general_sync_at to calendar_sync_status

Revision ID: 2d4e9f0a1c3b
Revises: 6d328702ea8e
Create Date: 2026-05-14 12:00:00.000000

"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "2d4e9f0a1c3b"
down_revision: str | Sequence[str] | None = "6d328702ea8e"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Upgrade schema."""
    op.add_column(
        "calendar_sync_status",
        sa.Column("last_general_sync_at", sa.DateTime(), nullable=True),
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_column("calendar_sync_status", "last_general_sync_at")
