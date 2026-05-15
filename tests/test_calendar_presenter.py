from app.modules.calendar.internal.infrastructure.presenter import render_calendars_fragment


def test_render_calendars_fragment_no_sources():
    data = {"sources": [], "sync_statuses": {}}
    html = render_calendars_fragment(data)
    assert "No calendars configured." in html


def test_render_calendars_fragment_with_source():
    sources = [
        {
            "id": 1,
            "label": "Work",
            "url": "https://calendar.example/ical",
            "color": "#3182ce",
        }
    ]
    sync_statuses = {
        1: {
            "sync_status": "ok",
            "last_synced_at": "2026-05-04",
            "next_sync_at": None,
            "error_message": None,
        }
    }
    data = {"sources": sources, "sync_statuses": sync_statuses}
    html = render_calendars_fragment(data)
    assert "Work" in html
    assert "https://calendar.example/ical" in html
    assert "Last synced" in html
