"""Repository ports for slideshow module."""

from typing import Any, Protocol

from sqlmodel import Session


class ISlideshowRepository(Protocol):
    """Persistence port for slideshow selection use cases."""

    def get_settings(self, session: Session) -> Any | None:
        """Return current app settings if present."""
        ...

    def list_photos_for_preset(self, session: Session, preset_id: int) -> list[Any]:
        """Return photos associated with a preset identifier."""
        ...
