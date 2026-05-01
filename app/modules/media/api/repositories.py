"""Repository ports for media module."""

from typing import Any, Protocol

from sqlmodel import Session


class IMediaRepository(Protocol):
    """Persistence port for media use cases."""

    def create_preset(self, session: Session, name: str) -> Any:
        """Create and persist a preset."""
        ...

    def get_preset(self, session: Session, preset_id: int) -> Any | None:
        """Return one preset by identifier."""
        ...

    def add_photo(self, session: Session, filename: str, preset_id: int) -> Any:
        """Stage a photo row in the current session."""
        ...

    def commit(self, session: Session) -> None:
        """Commit current transaction."""
        ...

    def refresh_photo(self, session: Session, photo: Any) -> None:
        """Refresh one photo row in-place."""
        ...

    def get_photo(self, session: Session, photo_id: int) -> Any | None:
        """Return one photo by identifier."""
        ...

    def delete_photo(self, session: Session, photo: Any) -> None:
        """Delete one photo row."""
        ...

    def list_presets(self, session: Session) -> list[Any]:
        """Return all presets."""
        ...

    def list_photos_for_preset(self, session: Session, preset_id: int) -> list[Any]:
        """Return all photos for one preset."""
        ...

    def get_photo_with_preset(self, session: Session, photo_id: int) -> Any | None:
        """Return one photo with eager-loaded preset relationship."""
        ...
