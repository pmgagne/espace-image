"""Public calendar module API."""

from app.modules.calendar.internal.infrastructure.presenter import (
    render_calendars_fragment,
)

from .interfaces import ICalendarService, get_calendar_service

__all__ = [
    "ICalendarService",
    "get_calendar_service",
    "render_calendars_fragment",
]
