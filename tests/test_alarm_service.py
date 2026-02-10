from datetime import UTC, datetime, timedelta
from types import SimpleNamespace

from sqlmodel import select

from app.db.models import AlarmEvent
from app.services.alarm_service import AlarmService


def test_format_alarm_all_day():
    now = datetime(2026, 2, 10, 12, 0, tzinfo=UTC)
    start = datetime(2026, 2, 9, 0, 0)
    end = datetime(2026, 2, 10, 0, 0)
    ev = SimpleNamespace(event_start=start, event_end=end, summary="All Day Event")

    formatted = AlarmService.format_alarm(ev, "1:uid", now)
    assert formatted is not None
    assert formatted["all_day"] is True
    assert formatted["uid"] == "1:uid"


def test_purge_old_dismissed_alarms(session):
    old_alarm = AlarmEvent(
        uid="old-to-purge",
        trigger_time=datetime.now() - timedelta(days=60),
        dismissed_at=datetime.now() - timedelta(days=31),
    )
    session.add(old_alarm)
    session.commit()

    AlarmService.purge_old_dismissed_alarms(session)

    remaining = session.exec(select(AlarmEvent).where(AlarmEvent.uid == "old-to-purge")).all()
    assert remaining == []
