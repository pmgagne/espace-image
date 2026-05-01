"""Data contracts for media module."""

from dataclasses import dataclass


@dataclass(frozen=True)
class PresetDTO:
    """Data transfer object for a preset."""

    id: int
    name: str


@dataclass(frozen=True)
class PhotoDTO:
    """Data transfer object for a photo."""

    id: int
    preset_id: int
    filename: str


@dataclass(frozen=True)
class GalleryContextDTO:
    """Data transfer object for gallery UI context."""

    presets: list[PresetDTO]
    selected_preset: PresetDTO | None
    photos: list[PhotoDTO]
