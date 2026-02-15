import os

from sqlmodel import SQLModel, create_engine

# Ensure data directory exists
os.makedirs("data", exist_ok=True)

sqlite_file_name = "data/db.sqlite"
sqlite_url = f"sqlite:///{sqlite_file_name}"

connect_args = {"check_same_thread": False}
engine = create_engine(sqlite_url, connect_args=connect_args)


def create_db_and_tables() -> None:
    """
    Create all database tables defined in SQLModel metadata.
    """
    SQLModel.metadata.create_all(engine)
