import sys

from sqlmodel import Session, select

from app.db.engine import create_db_and_tables, engine
from app.db.models import AppSettings, Preset


def _run_alembic_upgrade():
    """Run Alembic migrations programmatically using Alembic's API.

    Falls back silently if Alembic is not installed.
    """
    try:
        from alembic.config import Config

        from alembic import command
    except Exception:  # ImportError or similar
        print("Alembic not installed; skipping automatic migrations.")
        return

    cfg = Config("alembic.ini")
    try:
        print("Running Alembic migrations (programmatic): upgrade head")
        command.upgrade(cfg, "head")
        print("Alembic migrations applied successfully.")
    except Exception as e:
        print(f"Alembic migration failed: {e}")


def init():
    print("Initializing database...")
    create_db_and_tables()

    # Attempt to run Alembic migrations to update existing schemas
    _run_alembic_upgrade()

    with Session(engine) as session:
        # Check for existing default preset to avoid duplicates
        statement = select(Preset).where(Preset.name == "Default")
        results = session.exec(statement)
        preset = results.first()

        if not preset:
            print("Seeding default preset...")
            preset = Preset(name="Default")
            session.add(preset)
            session.commit()
            session.refresh(preset)
            print(f"Created Default Preset ID: {preset.id}")

        # Ensure AppSettings exists
        settings = session.exec(select(AppSettings)).first()
        if not settings:
            print("Seeding AppSettings...")
            settings = AppSettings(
                active_preset_id=preset.id,
                weather_latitude=45.5017,  # Default Montreal
                weather_longitude=-73.5673,
                weather_timezone="auto",
                slideshow_duration=30,
            )
            session.add(settings)
            session.commit()
            print("AppSettings created.")
        else:
            print("AppSettings already exist.")


if __name__ == "__main__":
    # Ensure script runs with the project's working directory on sys.path
    try:
        init()
    except Exception:
        print("init_db encountered an error", file=sys.stderr)
        raise
