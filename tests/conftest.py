import warnings
from unittest.mock import patch

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.pool import StaticPool
from sqlmodel import Session, SQLModel, create_engine

from app.db.session import get_session
from app.main import app as fastapi_app

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

    # We patch the function imported in app.main to prevent side effects on disk
    with patch("app.main.create_db_and_tables"), TestClient(fastapi_app) as client:
        yield client

    fastapi_app.dependency_overrides.clear()
