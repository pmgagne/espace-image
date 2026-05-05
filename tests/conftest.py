import warnings
from unittest.mock import AsyncMock, patch

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.pool import StaticPool
from sqlmodel import Session, SQLModel, create_engine

from app.db.session import get_session
from app.db.session_factory import SessionFactory
from app.main import app as fastapi_app
from app.modules.alarms.api.interfaces import get_alarms_service
from app.modules.alarms.internal.application.service import create_alarms_service
from app.modules.alarms.internal.infrastructure.repository import AlarmsRepository
from app.modules.calendar.api.interfaces import get_calendar_service
from app.modules.calendar.internal.application.service import create_calendar_service
from app.modules.calendar.internal.infrastructure.repository import CalendarRepository
from app.modules.calendar.internal.infrastructure.sync_gateway import CalendarSyncGateway
from app.modules.media.api.interfaces import get_media_service
from app.modules.media.internal.application.service import create_media_service
from app.modules.media.internal.infrastructure.image_ops import GalleryManager
from app.modules.media.internal.infrastructure.repository import MediaRepository
from app.modules.settings.api.interfaces import get_settings_service
from app.modules.settings.internal.application.service import create_settings_service
from app.modules.settings.internal.infrastructure.repository import SettingsRepository
from app.modules.slideshow.api.interfaces import get_slideshow_service
from app.modules.slideshow.internal.application.service import create_slideshow_service
from app.modules.slideshow.internal.infrastructure.repository import SlideshowRepository
from app.modules.weather.api.interfaces import get_weather_service
from app.modules.weather.internal.application.service import create_weather_service
from app.modules.weather.internal.infrastructure.gateway import WeatherGateway

# Suppress noisy third-party Deprecation/Runtime warnings during tests
warnings.filterwarnings(
    "ignore",
    message=r".*asyncio.iscoroutinefunction.*",
    category=DeprecationWarning,
)
warnings.filterwarnings(
    "ignore",
    message=r".*TemplateResponse\(name, \{.*'request'.*\}\).*",
    category=DeprecationWarning,
)
warnings.filterwarnings(
    "ignore",
    message=r"coroutine 'AsyncMockMixin._execute_mock_call' was never awaited",
    category=RuntimeWarning,
)

# Use in-memory SQLite for tests
# check_same_thread=False is needed for SQLite with multiple threads (FastAPI)
sqlite_url = "sqlite:///:memory:"
test_engine = create_engine(
    sqlite_url, connect_args={"check_same_thread": False}, poolclass=StaticPool
)


@pytest.fixture(name="session")
def session_fixture():
    """
    Creates a new database session for a test.
    Creates tables before the test and drops them after.
    """
    SQLModel.metadata.create_all(test_engine)
    with Session(test_engine) as session:
        yield session
    SQLModel.metadata.drop_all(test_engine)


@pytest.fixture(name="client")
def client_fixture(session: Session):
    """
    Returns a TestClient with the database session overridden.
    Patches the startup event to prevent the real DB file from being created.
    """

    def get_session_override():
        return session

    fastapi_app.dependency_overrides[get_session] = get_session_override

    # We patch asyncio.to_thread to avoid running the real Alembic upgrade during tests.
    # Tests previously patched `app.main._run_alembic_upgrade`; patching `asyncio.to_thread`
    # keeps tests independent of the implementation (whether migrations are run
    # via a helper function or inline) and avoids modifying application code.
    with (
        patch("asyncio.to_thread", new=AsyncMock(return_value=None)),
        TestClient(fastapi_app) as client,
    ):
        # Route-level DI now depends on module services instead of request Session.
        # Apply after startup so module loaders cannot overwrite these test overrides.
        test_session_factory = SessionFactory(test_engine)
        fastapi_app.dependency_overrides[get_settings_service] = lambda: create_settings_service(
            test_session_factory,
            SettingsRepository(),
        )
        fastapi_app.dependency_overrides[get_media_service] = lambda: create_media_service(
            test_session_factory,
            MediaRepository(),
            GalleryManager(),
        )
        fastapi_app.dependency_overrides[get_calendar_service] = lambda: create_calendar_service(
            test_session_factory,
            CalendarRepository(),
            CalendarSyncGateway(),
        )
        fastapi_app.dependency_overrides[get_alarms_service] = lambda: create_alarms_service(
            test_session_factory,
            AlarmsRepository(),
        )
        fastapi_app.dependency_overrides[get_slideshow_service] = lambda: create_slideshow_service(
            test_session_factory,
            SlideshowRepository(),
        )
        fastapi_app.dependency_overrides[get_weather_service] = lambda: create_weather_service(
            test_session_factory,
            WeatherGateway(),
        )
        yield client

    fastapi_app.dependency_overrides.clear()


@pytest.fixture(name="session_factory")
def session_factory_fixture() -> SessionFactory:
    """Return a SessionFactory bound to the in-memory test engine."""
    return SessionFactory(test_engine)
