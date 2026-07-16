from sqlmodel import select

from app.db.models import CalendarSource, CalendarSyncStatusEntry


def test_api_create_calendar_source_returns_json_and_persists(client, session):
    response = client.post(
        "/api/v1/calendar/sources",
        json={
            "label": "Work",
            "url": "https://example.com/work.ics",
            "color": "#112233",
        },
    )

    assert response.status_code == 201
    assert response.headers["content-type"].startswith("application/json")
    assert response.json()["label"] == "Work"
    assert response.json()["url"] == "https://example.com/work.ics"

    sources = session.exec(select(CalendarSource).where(CalendarSource.label == "Work")).all()
    assert len(sources) == 1


def test_api_delete_calendar_source(client, session):
    source = CalendarSource(
        label="Delete Me", url="https://example.com/delete.ics", color="#778899"
    )
    session.add(source)
    session.commit()
    session.refresh(source)
    source_id = source.id

    response = client.delete(f"/api/v1/calendar/sources/{source_id}")
    assert response.status_code == 204

    session.expire_all()
    assert session.get(CalendarSource, source_id) is None


def test_api_delete_calendar_source_sweeps_orphans(client, session):
    """Deleting a source is the only production code path that reclaims rows
    orphaned by a prior failed/partial cleanup — it must sweep them, not just
    delete the target source's own rows."""
    source = CalendarSource(
        label="Delete Me Too", url="https://example.com/delete2.ics", color="#334455"
    )
    session.add(source)
    session.commit()
    session.refresh(source)
    source_id = source.id

    # A row left orphaned by an earlier failure/deletion (no matching source).
    orphan_status = CalendarSyncStatusEntry(calendar_source_id=999999, sync_token="orphan")
    session.add(orphan_status)
    session.commit()

    response = client.delete(f"/api/v1/calendar/sources/{source_id}")
    assert response.status_code == 204

    session.expire_all()
    remaining_orphans = session.exec(
        select(CalendarSyncStatusEntry).where(CalendarSyncStatusEntry.calendar_source_id == 999999)
    ).all()
    assert remaining_orphans == []


def test_api_list_calendar_sources_and_sync_status_return_json(client, session):
    source = CalendarSource(label="Home", url="https://example.com/home.ics", color="#123456")
    session.add(source)
    session.commit()

    sources_response = client.get("/api/v1/calendar/sources")
    assert sources_response.status_code == 200
    assert sources_response.headers["content-type"].startswith("application/json")
    assert any(item["label"] == "Home" for item in sources_response.json())

    status_response = client.get("/api/v1/calendar/sync-status")
    assert status_response.status_code == 200
    assert status_response.headers["content-type"].startswith("application/json")
    assert isinstance(status_response.json(), list)


def test_api_calendar_sync_and_latest_sync_return_json(client):
    sync_response = client.post("/api/v1/calendar/sync")
    assert sync_response.status_code == 202
    assert sync_response.headers["content-type"].startswith("application/json")
    assert sync_response.json()["status"] in {"sync-complete", "sync-partial"}
    assert "calendar_sync_success" in sync_response.json()
    assert "alarms_sync_success" in sync_response.json()

    latest_sync_response = client.get("/api/v1/calendar/latest-sync")
    assert latest_sync_response.status_code == 200
    assert latest_sync_response.headers["content-type"].startswith("application/json")
    assert "latest_sync_utc" in latest_sync_response.json()


def test_api_calendar_events_return_json(client):
    response = client.get("/api/v1/calendar/events?days_back=1&days_ahead=1")
    assert response.status_code == 200
    assert response.headers["content-type"].startswith("application/json")
    assert isinstance(response.json(), list)
