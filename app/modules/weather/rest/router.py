"""Read-only JSON routes for weather operations."""

from fastapi import APIRouter, Depends, Query
from fastapi.encoders import jsonable_encoder
from fastapi.responses import JSONResponse

from app.modules.weather.api.interfaces import IWeatherService, get_weather_service

router = APIRouter(prefix="/api/v1/weather", tags=["api-weather"])


@router.get("/current")
async def get_current_weather(
    lat: float = Query(...),
    lon: float = Query(...),
    weather_service: IWeatherService = Depends(get_weather_service),
) -> JSONResponse:
    """Return normalized current weather for provided coordinates."""
    weather = await weather_service.get_current_weather(lat, lon)
    return JSONResponse(content=jsonable_encoder(weather))


@router.get("/location-name")
async def get_location_name(
    lat: float = Query(...),
    lon: float = Query(...),
    weather_service: IWeatherService = Depends(get_weather_service),
) -> JSONResponse:
    """Return reverse-geocoded display name for coordinates."""
    name = await weather_service.reverse_geocode(lat, lon)
    return JSONResponse(content={"name": name})


@router.get("/geocode")
async def geocode_location(
    q: str = Query(..., min_length=1),
    weather_service: IWeatherService = Depends(get_weather_service),
) -> JSONResponse:
    """Return geocoding result for a location query."""
    result = await weather_service.geocode_location(q)
    return JSONResponse(content=jsonable_encoder(result))
