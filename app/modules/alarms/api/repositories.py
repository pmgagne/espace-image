"""Repository ports for alarms module."""

from datetime import datetime
from typing import Any, Protocol
from uuid import UUID

from sqlmodel import Session


class IAlarmsRepository(Protocol):
    """Persistence port for alarms use cases."""

    def list_calendar_sources(self, session: Session) -> list[Any]:
        """Return all calendar sources."""
        ...

    def list_cached_events_in_window(
        self,
        session: Session,
        source_id: int,
        window_start: datetime,
        window_end: datetime,
    ) -> list[Any]:
        """Return cached events in a time window for one source."""
        ...

    def get_alarm_by_calendar_uid(
        self,
        session: Session,
        source_id: int,
        event_uid: str,
    ) -> Any | None:
        """Return alarm row by calendar source and event UID."""
        ...

    def get_alarm_by_uuid(self, session: Session, alarm_id: UUID) -> Any | None:
        """Return alarm row by UUID."""
        ...

    def get_cached_event_by_uid(
        self,
        session: Session,
        source_id: int,
        event_uid: str,
    ) -> Any | None:
        """Return cached event by source and UID."""
        ...

    def add_alarm(self, session: Session, alarm: Any) -> None:
        """Stage an alarm row for persistence in current transaction."""
        ...

    def list_ready_simulated_alarms(
        self,
        session: Session,
        now_naive: datetime,
    ) -> list[Any]:
        """Return simulated alarms ready to fire and not dismissed."""
        ...

    def list_dismissed_before(
        self,
        session: Session,
        purge_before: datetime,
    ) -> list[Any]:
        """Return dismissed alarms older than a threshold."""
        ...

    def list_triggered_before(
        self,
        session: Session,
        cutoff: datetime,
    ) -> list[Any]:
        """Return alarms whose trigger_time is older than a threshold."""
        ...

    def delete_alarm(self, session: Session, alarm: Any) -> None:
        """Delete one alarm row in current transaction."""
        ...

    def list_cached_events(self, session: Session) -> list[Any]:
        """Return all cached events for debug view."""
        ...

    def list_all_alarms(self, session: Session) -> list[Any]:
        """Return all alarm rows for debug view."""
        ...
