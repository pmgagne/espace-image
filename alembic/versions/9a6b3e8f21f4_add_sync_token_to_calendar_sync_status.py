"""add sync_token to calendar_sync_status

Revision ID: 9a6b3e8f21f4
Revises: 120becb0bbf1
Create Date: 2026-05-13 00:00:00.000000

"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "9a6b3e8f21f4"
down_revision: str | Sequence[str] | None = "120becb0bbf1"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Upgrade schema."""
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    cols = [c["name"] for c in inspector.get_columns("calendar_sync_status")]
    if "sync_token" not in cols:
        op.add_column("calendar_sync_status", sa.Column("sync_token", sa.String(), nullable=True))


def downgrade() -> None:
    """Downgrade schema."""
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    cols = [c["name"] for c in inspector.get_columns("calendar_sync_status")]
    if "sync_token" in cols:
        op.drop_column("calendar_sync_status", "sync_token")
