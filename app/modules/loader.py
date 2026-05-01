"""Composition root for module initialization and teardown."""

from fastapi import FastAPI

from .alarms import loader as alarms_loader
from .calendar import loader as calendar_loader
from .media import loader as media_loader
from .settings import loader as settings_loader
from .slideshow import loader as slideshow_loader
from .weather import loader as weather_loader


async def app_init(app: FastAPI) -> None:
    """Initialize module dependencies and startup wiring."""
    await alarms_loader.init(app)
    await calendar_loader.init(app)
    await media_loader.init(app)
    await settings_loader.init(app)
    await slideshow_loader.init(app)
    await weather_loader.init(app)


def app_post_init(app: FastAPI) -> None:
    """Run post-initialization hooks for modules."""
    alarms_loader.post_init(app)
    calendar_loader.post_init(app)
    media_loader.post_init(app)
    settings_loader.post_init(app)
    slideshow_loader.post_init(app)
    weather_loader.post_init(app)


async def app_teardown(app: FastAPI) -> None:
    """Run teardown hooks for modules."""
    await alarms_loader.teardown(app)
    await calendar_loader.teardown(app)
    await media_loader.teardown(app)
    await settings_loader.teardown(app)
    await slideshow_loader.teardown(app)
    await weather_loader.teardown(app)
