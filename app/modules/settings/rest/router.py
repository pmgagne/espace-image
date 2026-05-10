"""Atomic JSON routes for settings operations."""

from fastapi import APIRouter, Depends, HTTPException
from fastapi.encoders import jsonable_encoder
from fastapi.responses import JSONResponse

from app.modules.settings.api.exceptions import PresetNotFoundError
from app.modules.settings.api.interfaces import ISettingsService, get_settings_service

from .schemas import (
    ActivePresetRequest,
    DefaultAlarmPolicyRequest,
    SlideshowDurationRequest,
    WeatherLocationRequest,
)

router = APIRouter(prefix="/api/v1/settings", tags=["api-settings"])


def _current_settings_values(
    settings_service: ISettingsService,
) -> dict[str, int | float | bool | None]:
    """Return current settings values or model defaults for partial updates."""
    current = settings_service.get_settings()
    if current is None:
        return {
            "active_preset_id": None,
            "latitude": None,
            "longitude": None,
            "duration": 30,
            "default_alarm_for_all_events": False,
        }

    return {
        "active_preset_id": current.active_preset_id,
        "latitude": current.weather_latitude,
        "longitude": current.weather_longitude,
        "duration": current.slideshow_duration,
        "default_alarm_for_all_events": current.default_alarm_for_all_events,
    }


def _save_settings(
    settings_service: ISettingsService,
    *,
    active_preset_id: int | None,
    latitude: float | None,
    longitude: float | None,
    duration: int | None,
    default_alarm_for_all_events: bool,
) -> JSONResponse:
    """Validate and persist settings changes, translating public errors to HTTP."""
    try:
        settings_service.validate_settings_input(latitude, longitude, duration)
        settings = settings_service.save_settings(
            active_preset_id=active_preset_id,
            latitude=latitude,
            longitude=longitude,
            duration=duration,
            default_alarm_for_all_events=default_alarm_for_all_events,
        )
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    except PresetNotFoundError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc

    return JSONResponse(content=jsonable_encoder(settings))


@router.get("")
async def get_settings(
    settings_service: ISettingsService = Depends(get_settings_service),
) -> JSONResponse:
    """Return current application settings as JSON."""
    return JSONResponse(content=jsonable_encoder(settings_service.get_settings()))


@router.get("/presets")
async def list_presets(
    settings_service: ISettingsService = Depends(get_settings_service),
) -> JSONResponse:
    """Return available presets for settings-related clients."""
    return JSONResponse(content=jsonable_encoder(settings_service.list_presets()))


@router.put("/active-preset")
async def set_active_preset(
    payload: ActivePresetRequest,
    settings_service: ISettingsService = Depends(get_settings_service),
) -> JSONResponse:
    """Set the active preset while preserving other settings values."""
    current = _current_settings_values(settings_service)
    return _save_settings(
        settings_service,
        active_preset_id=payload.active_preset_id,
        latitude=current["latitude"],
        longitude=current["longitude"],
        duration=current["duration"],
        default_alarm_for_all_events=current["default_alarm_for_all_events"],
    )


@router.put("/slideshow-duration")
async def set_slideshow_duration(
    payload: SlideshowDurationRequest,
    settings_service: ISettingsService = Depends(get_settings_service),
) -> JSONResponse:
    """Set the slideshow duration while preserving other settings values."""
    current = _current_settings_values(settings_service)
    return _save_settings(
        settings_service,
        active_preset_id=current["active_preset_id"],
        latitude=current["latitude"],
        longitude=current["longitude"],
        duration=payload.slideshow_duration,
        default_alarm_for_all_events=current["default_alarm_for_all_events"],
    )


@router.put("/weather-location")
async def set_weather_location(
    payload: WeatherLocationRequest,
    settings_service: ISettingsService = Depends(get_settings_service),
) -> JSONResponse:
    """Set weather coordinates while preserving other settings values."""
    current = _current_settings_values(settings_service)
    return _save_settings(
        settings_service,
        active_preset_id=current["active_preset_id"],
        latitude=payload.latitude,
        longitude=payload.longitude,
        duration=current["duration"],
        default_alarm_for_all_events=current["default_alarm_for_all_events"],
    )


@router.put("/default-alarm-policy")
async def set_default_alarm_policy(
    payload: DefaultAlarmPolicyRequest,
    settings_service: ISettingsService = Depends(get_settings_service),
) -> JSONResponse:
    """Set the default alarm policy while preserving other settings values."""
    current = _current_settings_values(settings_service)
    return _save_settings(
        settings_service,
        active_preset_id=current["active_preset_id"],
        latitude=current["latitude"],
        longitude=current["longitude"],
        duration=current["duration"],
        default_alarm_for_all_events=payload.default_alarm_for_all_events,
    )
