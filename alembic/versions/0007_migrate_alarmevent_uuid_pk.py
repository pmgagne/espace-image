"""migrate_alarmevent_uuid_pk

Revision ID: 0007
Revises: 0006
Create Date: 2026-05-01

Reconstructs the alarmevent table to use a TEXT UUID primary key and adds
calendar_source_id / calendar_event_uid columns, dropping the old integer
id + uid composite-key design.

Downgrade is intentionally a no-op: the data transformation is not reversible
without data loss, which is acceptable for this deployment model.

Previously applied via raw sqlite3 table-copy dance in migrate_database().
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "0007"
down_revision: str | Sequence[str] | None = "0006"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Reconstruct alarmevent using batch_alter_table (SQLite-safe rename/copy)."""
    conn = op.get_bind()

    # Check whether this DB has the old schema (uid column present = old schema)
    result = conn.execute(sa.text("PRAGMA table_info(alarmevent)"))
    columns = [row[1] for row in result.fetchall()]

    if "uid" not in columns:
        # Already migrated or fresh DB — nothing to do
        return

    from uuid import uuid4

    # Read existing rows before restructuring
    rows = conn.execute(
        sa.text("SELECT id, uid, trigger_time, dismissed_at FROM alarmevent")
    ).fetchall()

    # Create the new table shape via batch_alter_table (handles SQLite constraints)
    with op.batch_alter_table(
        "alarmevent",
        table_args=(
            sa.Column("id", sa.Text(), primary_key=True, nullable=False),
            sa.Column("trigger_time", sa.DateTime(), nullable=False),
            sa.Column("dismissed_at", sa.DateTime(), nullable=True),
            sa.Column("calendar_source_id", sa.Integer(), nullable=True),
            sa.Column("calendar_event_uid", sa.Text(), nullable=True),
        ),
        recreate="always",
    ) as batch_op:
        batch_op.add_column(sa.Column("calendar_source_id", sa.Integer(), nullable=True))
        batch_op.add_column(sa.Column("calendar_event_uid", sa.Text(), nullable=True))
        batch_op.drop_column("uid")
        # Change id from integer to TEXT UUID
        batch_op.alter_column("id", type_=sa.Text(), nullable=False)

    # Repopulate with new UUIDs and parsed composite uid -> (source_id, event_uid)
    for old_id, uid, _trigger_time, _dismissed_at in rows:
        new_uuid = str(uuid4())
        calendar_source_id = None
        calendar_event_uid = None
        if uid and ":" in uid and not uid.startswith("test-") and not uid.startswith("mock-"):
            parts = uid.split(":", 1)
            try:
                calendar_source_id = int(parts[0])
                calendar_event_uid = parts[1]
            except (ValueError, IndexError):
                pass

        conn.execute(
            sa.text(
                "UPDATE alarmevent SET id=:new_id, calendar_source_id=:src, "
                "calendar_event_uid=:uid WHERE id=:old_id"
            ),
            {
                "new_id": new_uuid,
                "src": calendar_source_id,
                "uid": calendar_event_uid,
                "old_id": old_id,
            },
        )

    # Create indexes
    op.create_index("ix_alarmevent_calendar_source_id", "alarmevent", ["calendar_source_id"])
    op.create_index("ix_alarmevent_calendar_event_uid", "alarmevent", ["calendar_event_uid"])


def downgrade() -> None:
    """No-op: UUID PK migration is not reversible without data loss."""
    pass
