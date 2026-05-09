"""REST-only request models for calendar endpoints."""

from pydantic import BaseModel, Field


class CreateCalendarSourceRequest(BaseModel):
    """Request payload for creating a calendar source."""

    label: str = Field(min_length=1)
    url: str = Field(min_length=1)
    color: str = "#3182ce"


class UpdateCalendarDefaultAlarmRequest(BaseModel):
    """Request payload for updating default alarm policy on a source."""

    default_alarm_for_all_events: bool
