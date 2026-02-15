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

    with patch(
        "icalevents.icaldownload.ICalDownload.data_from_url", new_callable=AsyncMock
    ) as mock_data:
        mock_data.return_value = ics_content

        sources = [(1, "http://example.com/cal1.ics"), (2, "webcal://example.com/cal2.ics")]
        await CalendarService.get_all_alarms(sources)

        # We expect the downloader to be called twice
        assert mock_data.call_count == 2
