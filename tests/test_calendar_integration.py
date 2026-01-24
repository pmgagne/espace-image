from unittest.mock import AsyncMock, patch

import pytest

from app.services.calendar_service import CalendarService


@pytest.mark.anyio
async def test_get_all_alarms():
    # Mock httpx response
    ics_content = """BEGIN:VCALENDAR
VERSION:2.0
PRODID:-//hacksw/handcal//NONSGML v1.0//EN
BEGIN:VEVENT
UID:uid1@example.com
DTSTAMP:19970714T170000Z
ORGANIZER;CN=John Doe:MAILTO:john.doe@example.com
DTSTART:20260118T170000Z
DTEND:20260118T180000Z
SUMMARY:Bastille Day Party
END:VEVENT
END:VCALENDAR"""

    with patch("httpx.AsyncClient.get", new_callable=AsyncMock) as mock_get:
        mock_get.return_value.status_code = 200
        mock_get.return_value.text = ics_content
        mock_get.return_value.raise_for_status = lambda: None

        urls = ["http://example.com/cal1.ics", "webcal://example.com/cal2.ics"]
        await CalendarService.get_all_alarms(urls)

        # We expect fetch_ics to be called twice
        assert mock_get.call_count == 2
