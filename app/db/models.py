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

class AppSettings(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    active_preset_id: Optional[int] = Field(default=None, foreign_key="preset.id")
    weather_api_key: Optional[str] = Field(default=None)
    calendar_url: Optional[str] = Field(default=None)
    weather_location: Optional[str] = Field(default=None)

class AlarmEvent(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    uid: str = Field(index=True, unique=True)
    trigger_time: datetime
    dismissed_at: Optional[datetime] = Field(default=None)
