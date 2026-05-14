import asyncio
from datetime import UTC, datetime

from app.db.models import CalendarSource, CalendarSyncStatusEntry
from app.modules.calendar.api.contracts import CalendarSourceSyncReportDTO, CalendarSyncReportDTO
from app.modules.calendar.internal.application.service import create_calendar_service
from app.modules.calendar.internal.infrastructure.repository import CalendarRepository


class FakeSyncGateway:
    """Minimal sync gateway double for testing general sync decisions."""

    def __init__(self, report: CalendarSyncReportDTO) -> None:
        self.report = report
        self.normalize_called = False
        self.mark_called = False

    async def sync_calendar_events(self, session):
        await self.sync_calendar_events_with_report(session)

    async def sync_calendar_events_with_report(self, _session):
        return self.report

    async def normalize_alarm_occurrences(self, _session, start_date=None, days=30):
        self.normalize_called = True
        return 5

    async def fetch_ics(self, _url: str):
        return None

    async def mark_general_sync_completed(self, _session, _source_ids: list[int]) -> None:
        self.mark_called = True


def test_general_sync_skips_alarm_when_caldav_unchanged_and_already_done_today(
    session,
    session_factory,
):
    """General sync should skip alarm rebuild for unchanged CalDAV on same day."""
    source = CalendarSource(label="CalDAV", url="https://caldav.icloud.com/cal")
    session.add(source)
    session.commit()
    session.refresh(source)

    session.add(
        CalendarSyncStatusEntry(
            calendar_source_id=source.id,
            last_general_sync_at=datetime.now(UTC),
        )
    )
    session.commit()

    report = CalendarSyncReportDTO(
        source_reports=[
            CalendarSourceSyncReportDTO(
                calendar_source_id=source.id,
                calendar_source_url=source.url,
                sync_succeeded=True,
                changed=False,
                is_caldav=True,
            )
        ]
    )
    gateway = FakeSyncGateway(report)
    service = create_calendar_service(session_factory, CalendarRepository(), gateway)

    result = asyncio.run(service.general_sync(session=session))

    assert result.alarms_skipped is True
    assert result.alarms_skip_reason == "no-caldav-changes-and-already-synced-today"
    assert gateway.normalize_called is False


def test_general_sync_runs_alarm_when_non_caldav_source_exists(session, session_factory):
    """General sync should always normalize alarms when a non-CalDAV source exists."""
    source = CalendarSource(label="WebCal", url="webcal://example.com/test.ics")
    session.add(source)
    session.commit()
    session.refresh(source)

    session.add(
        CalendarSyncStatusEntry(
            calendar_source_id=source.id,
            last_general_sync_at=datetime.now(UTC),
        )
    )
    session.commit()

    report = CalendarSyncReportDTO(
        source_reports=[
            CalendarSourceSyncReportDTO(
                calendar_source_id=source.id,
                calendar_source_url=source.url,
                sync_succeeded=True,
                changed=None,
                is_caldav=False,
            )
        ]
    )
    gateway = FakeSyncGateway(report)
    service = create_calendar_service(session_factory, CalendarRepository(), gateway)

    result = asyncio.run(service.general_sync(session=session))

    assert result.alarms_skipped is False
    assert result.alarms_sync_success is True
    assert result.normalized_alarm_count == 5
    assert gateway.normalize_called is True
    assert gateway.mark_called is True
