"""Alarms module public interface."""

from typing import Any, Protocol

from app.config import ALARM_RETENTION_DAYS
from app.modules.alarms.api.contracts import AlarmEventDTO


class IAlarmsService(Protocol):
    """Public interface for alarms operations."""

    async def get_active_alarms(self) -> list[dict[str, Any]]:
        """
        Fetch active alarms that should be displayed.

        Args:
        Returns:
            List of alarm dictionaries with uid, name, start, end, trigger_time, all_day, tzid.
        """
        ...

    async def create_simulated_alarm(self, delay_seconds: int) -> AlarmEventDTO:
        """Create a simulated alarm that fires after the requested delay."""
        ...

    async def dismiss_alarm(self, alarm_uid: str) -> None:
        """
        Mark an alarm as dismissed.

        Args:
            alarm_uid: Composite UID of alarm (calendar_source_id:event_uid).
        """
        ...

    async def purge_old_alarms(self, retention_days: int = ALARM_RETENTION_DAYS) -> int:
        """Purge past alarm/event rows older than the retention window.

        Returns the number of rows deleted.
        """
        ...

    async def get_debug_alarm_state(self) -> dict[str, Any]:
        """
        Get cached calendar events and alarm events for debugging.

        Args:
        Returns:
            Dictionary with 'cached_events' and 'alarm_events' keys.
        """
        ...

    async def get_alarm_contexts(
        self, mock: bool = False, tz_offset: int | None = None
    ) -> list[dict[str, Any]]:
        """Return alarm payloads transformed for template rendering."""
        ...

    async def get_today_payload(
        self,
        tz_offset: int | None,
    ) -> dict[str, Any]:
        """Return today's alarms and events payload for frontend scheduling."""
        ...


def get_alarms_service() -> IAlarmsService:
    """Dependency injection token for alarms service."""
    raise NotImplementedError("Alarms service not initialized")
