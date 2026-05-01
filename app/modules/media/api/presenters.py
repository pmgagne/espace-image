"""Presenter ports for media module."""

from typing import Any, Protocol


class IMediaPresenter(Protocol):
    """Presentation port for media gallery HTML rendering."""

    def render_gallery_html(
        self,
        data: dict[str, Any],
        error_message: str | None = None,
    ) -> str:
        """Render gallery management partial HTML."""
        ...
