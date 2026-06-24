"""Atomic JSON routes for alarm operations."""

from datetime import UTC, datetime, timedelta

from fastapi import APIRouter, Depends, Query
from fastapi.encoders import jsonable_encoder
from fastapi.responses import JSONResponse

from app.config import ALARM_RETENTION_DAYS
from app.modules.alarms.api.interfaces import IAlarmsService, get_alarms_service

from .schemas import SimulateAlarmRequest

router = APIRouter(prefix="/api/v1/alarms", tags=["api-alarms"])


@router.get("/active")
async def get_active_alarms(
    alarms_service: IAlarmsService = Depends(get_alarms_service),
) -> JSONResponse:
    """Return active alarms as JSON."""
    alarms = await alarms_service.get_active_alarms()
    return JSONResponse(content=jsonable_encoder(alarms))


@router.get("/today")
async def get_today_payload(
    tz_offset: int | None = Query(None),
    alarms_service: IAlarmsService = Depends(get_alarms_service),
) -> JSONResponse:
    """Return today's alarms and events payload for frontend scheduling."""
    payload = await alarms_service.get_today_payload(tz_offset=tz_offset)
    return JSONResponse(content=jsonable_encoder(payload))


@router.post("/{alarm_id}/dismiss")
async def dismiss_alarm(
    alarm_id: str,
    mock: bool = Query(False),
    alarms_service: IAlarmsService = Depends(get_alarms_service),
) -> JSONResponse:
    """Dismiss one alarm by UUID or namespaced composite id."""
    if mock:
        return JSONResponse(content={"status": "mock-noop", "alarm_id": alarm_id})

    await alarms_service.dismiss_alarm(alarm_id)
    return JSONResponse(content={"status": "dismissed", "alarm_id": alarm_id})


@router.post("/simulated")
async def create_simulated_alarm(
    payload: SimulateAlarmRequest,
    alarms_service: IAlarmsService = Depends(get_alarms_service),
) -> JSONResponse:
    """Create one simulated alarm and return its JSON resource."""
    alarm = await alarms_service.create_simulated_alarm(payload.delay_seconds)
    return JSONResponse(status_code=201, content=jsonable_encoder(alarm))


@router.post("/purge-dismissed")
async def purge_old_dismissed_alarms(
    alarms_service: IAlarmsService = Depends(get_alarms_service),
) -> JSONResponse:
    """Purge dismissed alarms older than the retention window."""
    await alarms_service.purge_old_dismissed_alarms()
    purge_before = (datetime.now(UTC) - timedelta(days=ALARM_RETENTION_DAYS)).isoformat()
    return JSONResponse(content={"status": "purged", "purge_before_utc": purge_before})


@router.post("/purge-old")
async def purge_old_alarms(
    retention_days: int = Query(ALARM_RETENTION_DAYS, ge=1),
    alarms_service: IAlarmsService = Depends(get_alarms_service),
) -> JSONResponse:
    """Purge past alarm/event rows whose trigger_time is older than retention."""
    deleted = await alarms_service.purge_old_alarms(retention_days=retention_days)
    cutoff = (datetime.now(UTC) - timedelta(days=retention_days)).isoformat()
    return JSONResponse(
        content={"status": "purged", "deleted": deleted, "cutoff_utc": cutoff}
    )


@router.get("/debug/state")
async def get_debug_state(
    alarms_service: IAlarmsService = Depends(get_alarms_service),
) -> JSONResponse:
    """Return debug alarm state payload as JSON."""
    state = await alarms_service.get_debug_alarm_state()
    return JSONResponse(content=jsonable_encoder(state))
