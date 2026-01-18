from datetime import datetime
from typing import Optional, List
from sqlmodel import Field, SQLModel, Relationship


class Preset(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    name: str
    created_at: datetime = Field(default_factory=datetime.now)

    photos: List["Photo"] = Relationship(back_populates="preset")


class Photo(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    filename: str
    preset_id: int = Field(foreign_key="preset.id")
    uploaded_at: datetime = Field(default_factory=datetime.now)

    preset: Preset = Relationship(back_populates="photos")


class CalendarSource(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    label: str
    url: str  # WebCal or ICS URL
    color: Optional[str] = Field(default="#3182ce")  # Default blue


class AppSettings(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    active_preset_id: Optional[int] = Field(default=None, foreign_key="preset.id")
    weather_latitude: Optional[float] = Field(default=None)
    weather_longitude: Optional[float] = Field(default=None)
    weather_timezone: str = Field(default="auto")
    slideshow_duration: int = Field(default=30)  # in seconds


class AlarmEvent(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    uid: str = Field(index=True, unique=True)
    trigger_time: datetime
    dismissed_at: Optional[datetime] = Field(default=None)
