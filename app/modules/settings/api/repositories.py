"""Repository ports for settings module."""

from typing import Any, Protocol

from sqlmodel import Session


class ISettingsRepository(Protocol):
    """Persistence port for settings use cases."""

    def get_settings(self, session: Session) -> Any | None:
        """Return first settings row if present."""
        ...

    def list_presets(self, session: Session) -> list[tuple[Any, int]]:
        """Return all presets paired with their photo count."""
        ...

    def get_preset(self, session: Session, preset_id: int) -> tuple[Any, int] | None:
        """Return one preset by identifier paired with its photo count."""
        ...

    def save(self, session: Session, settings: Any) -> Any:
        """Persist settings row and return saved entity."""
        ...
