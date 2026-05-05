"""Session factory for database session management."""

from contextlib import contextmanager

from sqlalchemy.engine import Engine
from sqlmodel import Session


class SessionFactory:
    """
    Factory for creating transactional database sessions.

    This class abstracts session management, allowing:
    - Services to request sessions without knowing engine details
    - Tests to inject session factories with custom engines
    - Composition root to control session creation
    """

    def __init__(self, engine: Engine) -> None:
        """
        Initialize session factory with a database engine.

        Args:
            engine: SQLAlchemy Engine instance for session creation.
        """
        self._engine = engine

    @contextmanager
    def session_scope(self):
        """
        Provide a transactional session context.

        Yields:
            SQLModel Session for database operations.

        Usage:
            with factory.session_scope() as session:
                result = session.exec(select(User)).first()
        """
        with Session(self._engine) as session:
            yield session
