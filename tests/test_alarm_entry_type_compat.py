from datetime import UTC, datetime
from uuid import uuid4

from sqlalchemy import text
from sqlmodel import select

from app.db.models import AlarmEntryType, AlarmEvent


def test_alarm_entry_type_reads_legacy_uppercase_value(session) -> None:
    """Legacy uppercase enum values should deserialize without crashing."""
    alarm_id = str(uuid4())
    now = datetime.now(UTC).replace(tzinfo=None)

    session.execute(
        text(
            """
            INSERT INTO alarmevent (
                id,
                trigger_time,
                dismissed_at,
                calendar_source_id,
                calendar_event_uid,
                entry_type
            )
            VALUES (:id, :trigger_time, NULL, NULL, NULL, :entry_type)
            """
        ),
        {
            "id": alarm_id,
            "trigger_time": now,
            "entry_type": "ALARM",
        },
    )
    session.commit()

    alarms = list(session.exec(select(AlarmEvent)).all())

    assert len(alarms) == 1
    assert alarms[0].entry_type == AlarmEntryType.ALARM
