from datetime import UTC, datetime, timedelta

from app.db.session_factory import SessionFactory
from app.modules.alarms.internal.application.service import alarms_to_context


def test_alarms_sort_with_mixed_naive_and_aware_datetimes(session_factory: SessionFactory):
    """Regression test: ensure mixing naive and aware datetimes does not raise and sorts correctly."""
    # Aware datetime (UTC)
    aware_start = datetime(2026, 2, 15, 12, 0, tzinfo=UTC)
    aware_end = aware_start + timedelta(hours=1)

    # Naive datetime (no tzinfo) — one hour earlier
    naive_start = datetime(2026, 2, 15, 11, 0)
    naive_end = naive_start + timedelta(hours=1)

    active_alarms = [
        {
            "uid": "a-naive",
            "name": "Naive Event",
            "start": naive_start,
            "end": naive_end,
            "all_day": False,
        },
        {
            "uid": "b-aware",
            "name": "Aware Event",
            "start": aware_start,
            "end": aware_end,
            "all_day": False,
        },
    ]

    # Call the conversion to context — should not raise and should return contexts
    contexts = alarms_to_context(
        active_alarms,
        mock=False,
        tz_offset=None,
        session_factory=session_factory,
    )
    assert isinstance(contexts, list) and len(contexts) == 2

    # The aware event (12:00Z) should come before the naive (11:00 interpreted as UTC)
    first = contexts[0]
    second = contexts[1]

    assert "start_iso" in first and "start_iso" in second
    assert first["start_iso"].startswith("2026-02-15T12:00")
    assert second["start_iso"].startswith("2026-02-15T11:00")
