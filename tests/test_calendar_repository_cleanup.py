"""Tests for calendar repository cleanup behaviors."""

from sqlmodel import select

from app.db.models import (
    AlarmEvent,
    CalendarElement,
    CalendarSource,
    CalendarSyncStatusEntry,
)
from app.modules.calendar.internal.infrastructure.repository import CalendarRepository


def test_cleanup_orphans_deletes_orphan_rows(session):
    """cleanup_orphans should remove rows not tied to an active CalendarSource."""
    repo = CalendarRepository()

    # Create one active source
    src = CalendarSource(label="Active", url="https://example.com/cal/1")
    session.add(src)
    session.commit()
    session.refresh(src)

    # Add rows tied to active source
    status_active = CalendarSyncStatusEntry(calendar_source_id=src.id, sync_token="tok1")
    element_active = CalendarElement(
        calendar_source_id=src.id,
        uid="evt-1",
        raw_ics="BEGIN:VCALENDAR\nEND:VCALENDAR\n",
    )
    alarm_active = AlarmEvent(trigger_time=element_active.created_at, calendar_source_id=src.id)

    session.add_all([status_active, element_active, alarm_active])

    # Add orphan rows (calendar_source_id points at non-existent id)
    orphan_status = CalendarSyncStatusEntry(calendar_source_id=999, sync_token="orphan")
    orphan_element = CalendarElement(
        calendar_source_id=999,
        uid="evt-orphan",
        raw_ics="BEGIN:VCALENDAR\nEND:VCALENDAR\n",
    )
    orphan_alarm = AlarmEvent(trigger_time=element_active.created_at, calendar_source_id=999)

    session.add_all([orphan_status, orphan_element, orphan_alarm])
    session.commit()

    # Verify initial counts
    statuses_before = list(session.exec(select(CalendarSyncStatusEntry)).all())
    elements_before = list(session.exec(select(CalendarElement)).all())
    alarms_before = list(session.exec(select(AlarmEvent)).all())

    assert len(statuses_before) >= 2
    assert len(elements_before) >= 2
    assert len(alarms_before) >= 2

    # Run orphan cleanup
    deleted_statuses, deleted_elements, deleted_alarms = repo.cleanup_orphans(session)

    assert deleted_statuses == 1
    assert deleted_elements == 1
    assert deleted_alarms == 1

    # Ensure active rows remain
    remaining_statuses = list(
        session.exec(
            select(CalendarSyncStatusEntry).where(
                CalendarSyncStatusEntry.calendar_source_id == src.id
            )
        ).all()
    )
    remaining_elements = list(
        session.exec(
            select(CalendarElement).where(CalendarElement.calendar_source_id == src.id)
        ).all()
    )
    remaining_alarms = list(
        session.exec(select(AlarmEvent).where(AlarmEvent.calendar_source_id == src.id)).all()
    )

    assert len(remaining_statuses) == 1
    assert len(remaining_elements) == 1
    assert len(remaining_alarms) == 1


def test_cleanup_source_does_not_run_orphan_cleanup(session):
    """cleanup_source only removes per-source rows; orphan cleanup is a separate operation."""
    repo = CalendarRepository()

    # Create two sources, one to delete and one active
    to_delete = CalendarSource(label="ToDelete", url="https://example.com/cal/2")
    active = CalendarSource(label="Active2", url="https://example.com/cal/3")
    session.add_all([to_delete, active])
    session.commit()
    session.refresh(to_delete)
    session.refresh(active)

    # Add rows for to_delete and an orphan (non-existent source id)
    status_td = CalendarSyncStatusEntry(calendar_source_id=to_delete.id, sync_token="t1")
    elem_td = CalendarElement(
        calendar_source_id=to_delete.id,
        uid="td-1",
        raw_ics="BEGIN:VCALENDAR\nEND:VCALENDAR\n",
    )
    alarm_td = AlarmEvent(trigger_time=elem_td.created_at, calendar_source_id=to_delete.id)

    orphan_status = CalendarSyncStatusEntry(calendar_source_id=9999, sync_token="orphan2")
    session.add_all([status_td, elem_td, alarm_td, orphan_status])
    session.commit()

    # Run per-source cleanup — should remove only the target source's rows
    counts = repo.cleanup_source(session, to_delete.id)
    assert counts[0] == 1
    assert counts[1] == 1
    assert counts[2] == 1

    # Orphan must NOT be removed by cleanup_source (it has no knowledge of the source row
    # being deleted yet; orphan cleanup is done explicitly by callers after deletion).
    orphans_after = list(
        session.exec(
            select(CalendarSyncStatusEntry).where(
                CalendarSyncStatusEntry.calendar_source_id == 9999
            )
        ).all()
    )
    assert len(orphans_after) == 1

    # Explicit cleanup_orphans call (as a caller would do post-deletion) removes it.
    repo.cleanup_orphans(session)
    orphans_final = list(
        session.exec(
            select(CalendarSyncStatusEntry).where(
                CalendarSyncStatusEntry.calendar_source_id == 9999
            )
        ).all()
    )
    assert len(orphans_final) == 0
