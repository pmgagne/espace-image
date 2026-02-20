import logging
import os

from sqlmodel import SQLModel, create_engine

logger = logging.getLogger(__name__)

# Ensure data directory exists
os.makedirs("data", exist_ok=True)

sqlite_file_name = "data/db.sqlite"
sqlite_url = f"sqlite:///{sqlite_file_name}"

connect_args = {"check_same_thread": False}
engine = create_engine(sqlite_url, connect_args=connect_args)


def migrate_database() -> None:  # noqa: C901
    """
    Perform database migrations for schema changes.
    SQLModel.metadata.create_all() only creates new tables, not new columns.
    """
    import sqlite3

    db_path = sqlite_file_name
    if not os.path.exists(db_path):
        logger.info("Database does not exist yet, skipping migrations")
        return

    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    try:
        # Migration: Add default_alarm_for_all_events column to AppSettings if missing
        cursor.execute("PRAGMA table_info(appsettings)")
        appsettings_columns = [row[1] for row in cursor.fetchall()]
        if "default_alarm_for_all_events" not in appsettings_columns:
            logger.info("Adding default_alarm_for_all_events column to appsettings table")
            cursor.execute(
                "ALTER TABLE appsettings ADD COLUMN default_alarm_for_all_events BOOLEAN DEFAULT 0"
            )
            conn.commit()
            logger.info("Migration completed: default_alarm_for_all_events column added")
        else:
            logger.debug("default_alarm_for_all_events column already exists, no migration needed")

        # Migration: Add trigger_time and optional_trigger columns to calendar_event_cache if they don't exist
        cursor.execute("PRAGMA table_info(calendar_event_cache)")
        columns = [row[1] for row in cursor.fetchall()]

        # Add trigger_time column if missing
        if "trigger_time" not in columns:
            logger.info("Adding trigger_time column to calendar_event_cache table")
            cursor.execute("ALTER TABLE calendar_event_cache ADD COLUMN trigger_time TIMESTAMP")
            cursor.execute(
                "CREATE INDEX IF NOT EXISTS ix_calendar_event_cache_trigger_time "
                "ON calendar_event_cache (trigger_time)"
            )
            conn.commit()
            logger.info("Migration completed: trigger_time column added")
        else:
            logger.debug("trigger_time column already exists, no migration needed")

        # Add optional_trigger column if missing
        if "optional_trigger" not in columns:
            logger.info("Adding optional_trigger column to calendar_event_cache table")
            cursor.execute(
                "ALTER TABLE calendar_event_cache ADD COLUMN optional_trigger BOOLEAN DEFAULT 0"
            )
            cursor.execute(
                "CREATE INDEX IF NOT EXISTS ix_calendar_event_cache_optional_trigger "
                "ON calendar_event_cache (optional_trigger)"
            )
            conn.commit()
            logger.info("Migration completed: optional_trigger column added")
        else:
            logger.debug("optional_trigger column already exists, no migration needed")

        # Add event_tz column if missing (store original TZID from ICS)
        if "event_tz" not in columns:
            logger.info("Adding event_tz column to calendar_event_cache table")
            cursor.execute("ALTER TABLE calendar_event_cache ADD COLUMN event_tz TEXT")
            cursor.execute(
                "CREATE INDEX IF NOT EXISTS ix_calendar_event_cache_event_tz ON calendar_event_cache (event_tz)"
            )
            conn.commit()
            logger.info("Migration completed: event_tz column added")
        else:
            logger.debug("event_tz column already exists, no migration needed")

        # Migration: Add default_alarm_for_all_events column to calendarsource if missing
        cursor.execute("PRAGMA table_info(calendarsource)")
        cs_columns = [row[1] for row in cursor.fetchall()]
        if "default_alarm_for_all_events" not in cs_columns:
            logger.info("Adding default_alarm_for_all_events column to calendarsource table")
            cursor.execute(
                "ALTER TABLE calendarsource ADD COLUMN default_alarm_for_all_events BOOLEAN DEFAULT 0"
            )
            conn.commit()
            logger.info(
                "Migration completed: default_alarm_for_all_events column added to calendarsource"
            )
        else:
            logger.debug(
                "default_alarm_for_all_events column already exists on calendarsource, no migration needed"
            )

        # Migration: Convert AlarmEvent to use UUID primary key
        cursor.execute("PRAGMA table_info(alarmevent)")
        alarm_columns = [row[1] for row in cursor.fetchall()]

        if "uid" in alarm_columns:
            logger.info("Migrating AlarmEvent table to UUID primary key")

            # Step 1: Create new table with UUID schema
            cursor.execute("""
                CREATE TABLE alarmevent_new (
                    id TEXT PRIMARY KEY NOT NULL,
                    trigger_time TIMESTAMP NOT NULL,
                    dismissed_at TIMESTAMP,
                    calendar_source_id INTEGER,
                    calendar_event_uid TEXT
                )
            """)

            # Step 2: Create indexes
            cursor.execute(
                "CREATE INDEX ix_alarmevent_new_calendar_source_id "
                "ON alarmevent_new(calendar_source_id)"
            )
            cursor.execute(
                "CREATE INDEX ix_alarmevent_new_calendar_event_uid "
                "ON alarmevent_new(calendar_event_uid)"
            )

            # Step 3: Migrate existing data with UUID generation
            cursor.execute("SELECT id, uid, trigger_time, dismissed_at FROM alarmevent")
            existing_alarms = cursor.fetchall()

            from uuid import uuid4

            for _old_id, uid, trigger_time, dismissed_at in existing_alarms:
                new_uuid = str(uuid4())

                # Parse composite UID to extract calendar relationship
                calendar_source_id = None
                calendar_event_uid = None

                if (
                    uid
                    and ":" in uid
                    and not uid.startswith("test-")
                    and not uid.startswith("mock-")
                ):
                    # Parse composite format: "source_id:event_uid"
                    parts = uid.split(":", 1)
                    try:
                        calendar_source_id = int(parts[0])
                        calendar_event_uid = parts[1]
                    except (ValueError, IndexError):
                        # Invalid format, leave as NULL
                        pass

                cursor.execute(
                    """
                    INSERT INTO alarmevent_new (id, trigger_time, dismissed_at,
                                                 calendar_source_id, calendar_event_uid)
                    VALUES (?, ?, ?, ?, ?)
                """,
                    (new_uuid, trigger_time, dismissed_at, calendar_source_id, calendar_event_uid),
                )

            # Step 4: Drop old table and rename new table
            cursor.execute("DROP TABLE alarmevent")
            cursor.execute("ALTER TABLE alarmevent_new RENAME TO alarmevent")

            conn.commit()
            logger.info("Migration completed: AlarmEvent now uses UUID primary key")
        else:
            logger.debug("AlarmEvent table already migrated to UUID, skipping")

    except Exception as e:
        logger.error("Migration failed: %s", e)
        conn.rollback()
        raise
    finally:
        conn.close()


def create_db_and_tables() -> None:
    """
    Create all database tables defined in SQLModel metadata.
    Then run migrations for schema changes.
    """
    SQLModel.metadata.create_all(engine)
    migrate_database()
