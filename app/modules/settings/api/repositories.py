"""Repository ports for settings module."""

from typing import Any, Protocol

from sqlmodel import Session


class ISettingsRepository(Protocol):
    """Persistence port for settings use cases."""

    def get_settings(self, session: Session) -> Any | None:
        """Return first settings row if present."""
        ...

    def list_presets(self, session: Session) -> list[Any]:
        """Return all presets."""
        ...

    def get_preset(self, session: Session, preset_id: int) -> Any | None:
        """Return one preset by identifier."""
        ...

    def save(self, session: Session, settings: Any) -> Any:
        """Persist settings row and return saved entity."""
        ...
