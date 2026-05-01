"""Repository ports for calendar module."""

from datetime import datetime
from typing import Any, Protocol

from sqlmodel import Session


class ICalendarRepository(Protocol):
    """Persistence port for calendar use cases."""

    def list_events_in_window(
        self,
        session: Session,
        window_start: datetime,
        window_end: datetime,
    ) -> list[Any]:
        """Return cached events intersecting the requested time window."""
        ...

    def create_source(
        self,
        session: Session,
        label: str,
        url: str,
        color: str,
    ) -> Any:
        """Create and persist one calendar source."""
        ...

    def get_source(self, session: Session, source_id: int) -> Any | None:
        """Return one calendar source by identifier."""
        ...

    def save_source(self, session: Session, source: Any) -> Any:
        """Persist calendar source updates."""
        ...

    def delete_source(self, session: Session, source: Any) -> None:
        """Delete one calendar source row."""
        ...

    def list_statuses(self, session: Session) -> list[Any]:
        """Return all sync status rows."""
        ...

    def list_sources(self, session: Session) -> list[Any]:
        """Return all calendar source rows."""
        ...

    def get_status_for_source(
        self,
        session: Session,
        source_id: int,
    ) -> Any | None:
        """Return sync status for one source identifier."""
        ...
