from datetime import datetime

from sqlmodel import Field, Relationship, SQLModel


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
