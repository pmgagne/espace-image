"""Storage ports for media module."""

from pathlib import Path
from typing import Protocol


class IMediaStorage(Protocol):
    """Filesystem/storage port for media uploads."""

    def save_upload(
        self,
        file_content: bytes,
        filename: str,
        preset_name: str = "Default",
    ) -> tuple[Path, str]:
        """Save uploaded content and return path plus stored filename."""
        ...

    def delete_photo(self, filename: str, preset_name: str = "Default") -> bool:
        """Delete one stored file if present."""
        ...
