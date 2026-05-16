from datetime import UTC, datetime

from sqlmodel import select

from app.db.models import AlarmEntryType, AlarmEvent


def test_alarm_entry_type_round_trip(session) -> None:
    """Alarm entry_type values should persist and deserialize as enum values."""
    alarm = AlarmEvent(
        trigger_time=datetime.now(UTC),
        entry_type=AlarmEntryType.ALARM,
    )
    session.add(alarm)
    session.commit()

    alarms = list(session.exec(select(AlarmEvent)).all())

    assert len(alarms) == 1
    assert alarms[0].entry_type == AlarmEntryType.ALARM
