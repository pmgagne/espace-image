"""rename_calendar_event_cache_to_calendar_elements

Revision ID: 6d328702ea8e
Revises: 9a6b3e8f21f4
Create Date: 2026-05-13 21:31:00.890712

"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "6d328702ea8e"
down_revision: str | Sequence[str] | None = "9a6b3e8f21f4"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def _has_table(name: str) -> bool:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    return name in set(inspector.get_table_names())


def _has_column(table: str, column: str) -> bool:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    return column in {c["name"] for c in inspector.get_columns(table)}


def upgrade() -> None:
    if _has_table("calendar_event_cache") and not _has_table("calendar_elements"):
        op.rename_table("calendar_event_cache", "calendar_elements")
    elif _has_table("calendar_events") and not _has_table("calendar_elements"):
        op.rename_table("calendar_events", "calendar_elements")
    elif not _has_table("calendar_elements"):
        op.create_table(
            "calendar_elements",
            sa.Column("id", sa.Integer(), nullable=False),
            sa.Column("calendar_source_id", sa.Integer(), nullable=False),
            sa.Column("uid", sa.String(), nullable=False),
            sa.Column("event_start", sa.DateTime(), nullable=True),
            sa.Column("event_end", sa.DateTime(), nullable=True),
            sa.Column("event_tz", sa.String(), nullable=True),
            sa.Column("summary", sa.String(), nullable=False, server_default=""),
            sa.Column("description", sa.String(), nullable=False, server_default=""),
            sa.Column("location", sa.String(), nullable=False, server_default=""),
            sa.Column("all_day", sa.Boolean(), nullable=False, server_default=sa.text("0")),
            sa.Column("trigger_time", sa.DateTime(), nullable=True),
            sa.Column(
                "optional_trigger",
                sa.Boolean(),
                nullable=False,
                server_default=sa.text("0"),
            ),
            sa.Column("href", sa.String(), nullable=False, server_default=""),
            sa.Column("etag", sa.String(), nullable=True),
            sa.Column("raw_ics", sa.String(), nullable=False, server_default=""),
            sa.Column("created_at", sa.DateTime(), nullable=False),
            sa.ForeignKeyConstraint(["calendar_source_id"], ["calendarsource.id"]),
            sa.PrimaryKeyConstraint("id"),
            sa.UniqueConstraint("calendar_source_id", "uid"),
        )

    if _has_table("calendar_elements"):
        with op.batch_alter_table("calendar_elements") as batch_op:
            if not _has_column("calendar_elements", "href"):
                batch_op.add_column(
                    sa.Column("href", sa.String(), nullable=False, server_default="")
                )
            if not _has_column("calendar_elements", "etag"):
                batch_op.add_column(sa.Column("etag", sa.String(), nullable=True))
            if not _has_column("calendar_elements", "raw_ics"):
                batch_op.add_column(
                    sa.Column("raw_ics", sa.String(), nullable=False, server_default="")
                )


def downgrade() -> None:
    if _has_table("calendar_elements") and not _has_table("calendar_event_cache"):
        op.rename_table("calendar_elements", "calendar_event_cache")
