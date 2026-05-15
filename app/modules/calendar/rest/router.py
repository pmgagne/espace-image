"""Atomic JSON routes for calendar operations."""

from fastapi import APIRouter, Depends, HTTPException, Query, Response, status
from fastapi.encoders import jsonable_encoder
from fastapi.responses import JSONResponse

from app.modules.calendar.api.interfaces import ICalendarService, get_calendar_service

from .schemas import CreateCalendarSourceRequest

router = APIRouter(prefix="/api/v1/calendar", tags=["api-calendar"])


@router.get("/sources")
async def list_sources(
    calendar_service: ICalendarService = Depends(get_calendar_service),
) -> JSONResponse:
    """Return calendar source resources as JSON."""
    data = await calendar_service.get_calendars_for_ui()
    return JSONResponse(content=jsonable_encoder(data.get("sources", [])))


@router.post("/sources")
async def create_source(
    payload: CreateCalendarSourceRequest,
    calendar_service: ICalendarService = Depends(get_calendar_service),
) -> JSONResponse:
    """Create a calendar source and return the created resource."""
    source = await calendar_service.create_source(payload.label, payload.url, payload.color)
    return JSONResponse(status_code=status.HTTP_201_CREATED, content=jsonable_encoder(source))


@router.delete("/sources/{source_id}")
async def delete_source(
    source_id: int,
    calendar_service: ICalendarService = Depends(get_calendar_service),
) -> Response:
    """Delete a calendar source resource."""
    deleted = await calendar_service.delete_source(source_id)
    if not deleted:
        raise HTTPException(status_code=404, detail="Calendar source not found")
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.get("/sync-status")
async def get_sync_status(
    calendar_service: ICalendarService = Depends(get_calendar_service),
) -> JSONResponse:
    """Return calendar sync status rows as JSON."""
    statuses = await calendar_service.get_sync_status()
    return JSONResponse(content=jsonable_encoder(statuses))


@router.post("/sync")
async def sync_calendars(
    calendar_service: ICalendarService = Depends(get_calendar_service),
) -> JSONResponse:
    """Trigger calendar synchronization and return a JSON operation result."""
    result = await calendar_service.general_sync()
    payload = {
        "status": "sync-complete" if result.calendar_sync_success else "sync-partial",
        "calendar_sync_success": result.calendar_sync_success,
        "alarms_sync_success": result.alarms_sync_success,
        "alarms_skipped": result.alarms_skipped,
        "alarms_skip_reason": result.alarms_skip_reason,
        "normalized_alarm_count": result.normalized_alarm_count,
    }
    return JSONResponse(status_code=status.HTTP_202_ACCEPTED, content=payload)


@router.get("/events")
async def get_events(
    days_back: int = Query(7, ge=0, le=31),
    days_ahead: int = Query(7, ge=0, le=31),
    calendar_service: ICalendarService = Depends(get_calendar_service),
) -> JSONResponse:
    """Return calendar events in the requested window as JSON."""
    events = await calendar_service.get_calendar_events_in_window(
        days_back=days_back,
        days_ahead=days_ahead,
    )
    return JSONResponse(content=jsonable_encoder(events))


@router.get("/latest-sync")
async def get_latest_sync(
    calendar_service: ICalendarService = Depends(get_calendar_service),
) -> JSONResponse:
    """Return latest successful sync timestamp as JSON."""
    latest_sync = await calendar_service.get_latest_sync_utc_iso()
    return JSONResponse(content={"latest_sync_utc": latest_sync})
