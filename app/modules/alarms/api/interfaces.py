"""Alarms module public interface."""

from typing import Any, Protocol

from sqlmodel import Session


class IAlarmsService(Protocol):
    """Public interface for alarms operations."""

    async def get_active_alarms(self, session: Session) -> list[dict[str, Any]]:
        """
        Fetch active alarms that should be displayed.

        Args:
            session: Database session.

        Returns:
            List of alarm dictionaries with uid, name, start, end, trigger_time, all_day, tzid.
        """
        ...

    async def dismiss_alarm(self, alarm_uid: str, session: Session) -> None:
        """
        Mark an alarm as dismissed.

        Args:
            alarm_uid: Composite UID of alarm (calendar_source_id:event_uid).
            session: Database session.
        """
        ...

    async def purge_old_dismissed_alarms(self, session: Session) -> None:
        """Purge dismissed alarms older than 30 days."""
        ...


def get_alarms_service() -> IAlarmsService:
    """Dependency injection token for alarms service."""
    raise NotImplementedError("Alarms service not initialized")
