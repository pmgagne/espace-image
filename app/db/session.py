from collections.abc import Generator

from sqlmodel import Session

from app.db.engine import engine


def get_session() -> Generator[Session]:
    """
    Yield a SQLModel Session for database operations.

    Yields:
        Session: A SQLModel session object.
    """
    with Session(engine) as session:
        yield session
