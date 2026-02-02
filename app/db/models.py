from datetime import datetime
from enum import Enum as PyEnum

from sqlalchemy import UniqueConstraint
from sqlmodel import Field, Relationship, SQLModel


class CalendarSyncStatus(str, PyEnum):
    """Status of calendar synchronization."""

    PENDING = "pending"
    SYNCING = "syncing"
    SUCCESS = "success"
    FAILED = "failed"


class Preset(SQLModel, table=True):
    id: int | None = Field(default=None, primary_key=True)
    name: str
    created_at: datetime = Field(default_factory=datetime.now)

    photos: list["Photo"] = Relationship(back_populates="preset")


class Photo(SQLModel, table=True):
    id: int | None = Field(default=None, primary_key=True)
    filename: str
    preset_id: int = Field(foreign_key="preset.id")
    uploaded_at: datetime = Field(default_factory=datetime.now)

    preset: Preset = Relationship(back_populates="photos")


class CalendarSource(SQLModel, table=True):
    id: int | None = Field(default=None, primary_key=True)
    label: str
    url: str  # WebCal or ICS URL
    color: str | None = Field(default="#3182ce")  # Default blue


class AppSettings(SQLModel, table=True):
    id: int | None = Field(default=None, primary_key=True)
    active_preset_id: int | None = Field(default=None, foreign_key="preset.id")
    weather_latitude: float | None = Field(default=None)
    weather_longitude: float | None = Field(default=None)
    weather_timezone: str = Field(default="auto")
    slideshow_duration: int = Field(default=30)  # in seconds


class AlarmEvent(SQLModel, table=True):
    id: int | None = Field(default=None, primary_key=True)
    uid: str = Field(index=True, unique=True)
    trigger_time: datetime
    dismissed_at: datetime | None = Field(default=None)


class CalendarEventCache(SQLModel, table=True):
    """Cached calendar events from ICS sources within the 1-week window."""

    __tablename__ = "calendar_event_cache"
    __table_args__ = (UniqueConstraint("calendar_source_id", "uid"),)

    id: int | None = Field(default=None, primary_key=True)
    calendar_source_id: int = Field(foreign_key="calendarsource.id", index=True)
    uid: str = Field(index=True)
    event_start: datetime = Field(index=True)
    event_end: datetime = Field(index=True)
    summary: str
    description: str = Field(default="")
    location: str = Field(default="")
    created_at: datetime = Field(default_factory=datetime.now)


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
