from datetime import UTC, datetime
from enum import StrEnum
from uuid import UUID, uuid4

from sqlalchemy import UniqueConstraint
from sqlmodel import Field, Relationship, SQLModel


class CalendarSyncStatus(StrEnum):
    """Status of calendar synchronization."""

    PENDING = "pending"
    SYNCING = "syncing"
    SUCCESS = "success"
    FAILED = "failed"


class Preset(SQLModel, table=True):
    id: int | None = Field(default=None, primary_key=True)
    name: str
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))

    photos: list["Photo"] = Relationship(back_populates="preset")


class Photo(SQLModel, table=True):
    id: int | None = Field(default=None, primary_key=True)
    filename: str
    preset_id: int = Field(foreign_key="preset.id")
    uploaded_at: datetime = Field(default_factory=lambda: datetime.now(UTC))

    preset: Preset = Relationship(back_populates="photos")


class CalendarSource(SQLModel, table=True):
    id: int | None = Field(default=None, primary_key=True)
    label: str
    url: str  # WebCal or ICS URL
    color: str | None = Field(default="#3182ce")  # Default blue
    default_alarm_for_all_events: bool = Field(
        default=False,
        description="If true, add a default alarm at midnight for events without VALARM (per-calendar)",
    )


class AppSettings(SQLModel, table=True):
    id: int | None = Field(default=None, primary_key=True)
    active_preset_id: int | None = Field(default=None, foreign_key="preset.id")
    weather_latitude: float | None = Field(default=None)
    weather_longitude: float | None = Field(default=None)
    weather_timezone: str = Field(default="auto")
    slideshow_duration: int = Field(default=30)  # in seconds
    default_alarm_for_all_events: bool = Field(
        default=False,
        description="If true, add a default alarm at midnight for events with no VALARM",
    )


class AlarmEvent(SQLModel, table=True):
    __mapper_args__ = {"confirm_deleted_rows": False}

    id: UUID = Field(default_factory=uuid4, primary_key=True)
    trigger_time: datetime
    dismissed_at: datetime | None = Field(default=None)

    # Optional: Link to calendar event (null for test/simulated alarms)
    calendar_source_id: int | None = Field(default=None, index=True)
    calendar_event_uid: str | None = Field(default=None, index=True)


class CalendarElement(SQLModel, table=True):
    """Raw calendar items fetched from calendar sources without event processing."""

    __tablename__ = "calendar_elements"
    __table_args__ = (UniqueConstraint("calendar_source_id", "uid"),)

    id: int | None = Field(default=None, primary_key=True)
    calendar_source_id: int = Field(foreign_key="calendarsource.id", index=True)
    uid: str = Field(index=True)
    event_start: datetime | None = Field(default=None, index=True)
    event_end: datetime | None = Field(default=None, index=True)
    event_tz: str | None = Field(default=None, index=True)
    summary: str = Field(default="")
    description: str = Field(default="")
    location: str = Field(default="")
    all_day: bool = Field(default=False, index=True)
    trigger_time: datetime | None = Field(default=None, index=True)
    optional_trigger: bool = Field(default=False, index=True)
    href: str = Field(default="")
    etag: str | None = Field(default=None)
    raw_ics: str
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))


# Compatibility alias during transition from parsed event cache to raw elements.
CalendarEvent = CalendarElement


class CalendarSyncStatusEntry(SQLModel, table=True):
    """Tracks synchronization status per calendar source."""

    __tablename__ = "calendar_sync_status"

    id: int | None = Field(default=None, primary_key=True)
    calendar_source_id: int = Field(foreign_key="calendarsource.id", index=True, unique=True)
    last_synced_at: datetime | None = Field(default=None)
    next_sync_at: datetime | None = Field(default=None)
    sync_status: CalendarSyncStatus = Field(default=CalendarSyncStatus.PENDING)
    error_message: str = Field(default="")
    error_count: int = Field(default=0)
    last_error_at: datetime | None = Field(default=None)
    sync_token: str | None = Field(default=None)
    last_general_sync_at: datetime | None = Field(default=None)
