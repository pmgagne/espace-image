"""Atomic JSON routes for alarm operations."""

from datetime import UTC, datetime, timedelta

from fastapi import APIRouter, Depends, Query
from fastapi.encoders import jsonable_encoder
from fastapi.responses import JSONResponse

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
    """Purge dismissed alarms older than 30 days."""
    await alarms_service.purge_old_dismissed_alarms()
    purge_before = (datetime.now(UTC) - timedelta(days=30)).isoformat()
    return JSONResponse(content={"status": "purged", "purge_before_utc": purge_before})


@router.get("/debug/state")
async def get_debug_state(
    alarms_service: IAlarmsService = Depends(get_alarms_service),
) -> JSONResponse:
    """Return debug alarm state payload as JSON."""
    state = await alarms_service.get_debug_alarm_state()
    return JSONResponse(content=jsonable_encoder(state))
