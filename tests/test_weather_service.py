"""Tests for WeatherModuleService normalisation and fallback logic.

The service is exercised against a fake IWeatherGateway (AsyncMock) — no HTTP,
no DB.  This validates the service-layer normalisation and error-handling
branches independently of the infrastructure code.
"""

import asyncio
from unittest.mock import AsyncMock

import pytest

from app.modules.weather.api.interfaces import WeatherData, WeatherLocationResult
from app.modules.weather.internal.application.service import WeatherModuleService


def _make_service(gateway):
    """Return a WeatherModuleService with a fake gateway (session_factory unused here)."""
    return WeatherModuleService(session_factory=None, gateway=gateway)


# ---------------------------------------------------------------------------
# get_current_weather
# ---------------------------------------------------------------------------


def test_get_current_weather_maps_full_dict():
    gateway = AsyncMock()
    gateway.get_current_weather.return_value = {
        "temp": 22,
        "condition": "Ciel dégagé",
        "location": "45.50, -73.57",
    }
    service = _make_service(gateway)
    result = asyncio.run(service.get_current_weather(45.50, -73.57))

    assert result == WeatherData(temp=22, condition="Ciel dégagé", location="45.50, -73.57")


def test_get_current_weather_uses_defaults_on_empty_dict():
    gateway = AsyncMock()
    gateway.get_current_weather.return_value = {}
    service = _make_service(gateway)
    result = asyncio.run(service.get_current_weather(0.0, 0.0))

    assert result.temp == "--"
    assert result.condition == "Service Error"
    assert result.location == "Unavailable"


# ---------------------------------------------------------------------------
# geocode_location
# ---------------------------------------------------------------------------


def test_geocode_location_maps_valid_dict():
    gateway = AsyncMock()
    gateway.geocode_location.return_value = {
        "lat": 45.5017,
        "lon": -73.5673,
        "name": "Montréal, Canada",
    }
    service = _make_service(gateway)
    result = asyncio.run(service.geocode_location("Montréal"))

    assert result == WeatherLocationResult(lat=45.5017, lon=-73.5673, name="Montréal, Canada")


def test_geocode_location_returns_none_when_gateway_returns_none():
    gateway = AsyncMock()
    gateway.geocode_location.return_value = None
    service = _make_service(gateway)
    result = asyncio.run(service.geocode_location("nowhere"))

    assert result is None


def test_geocode_location_raises_on_missing_key():
    gateway = AsyncMock()
    # dict has "lat" but missing "lon" and "name" — float() succeeds, but dict["lon"] KeyErrors
    gateway.geocode_location.return_value = {"lat": 45.5}
    service = _make_service(gateway)

    with pytest.raises(KeyError):
        asyncio.run(service.geocode_location("partial"))


def test_geocode_location_raises_on_non_numeric_lat():
    gateway = AsyncMock()
    gateway.geocode_location.return_value = {"lat": "not-a-number", "lon": 0.0, "name": "Err"}
    service = _make_service(gateway)

    with pytest.raises(ValueError):
        asyncio.run(service.geocode_location("bad"))


# ---------------------------------------------------------------------------
# get_location_name
# ---------------------------------------------------------------------------


def test_get_location_name_returns_empty_string_when_lat_is_none():
    service = _make_service(AsyncMock())
    result = asyncio.run(service.get_location_name(None, -73.57))
    assert result == ""


def test_get_location_name_returns_empty_string_when_lon_is_none():
    service = _make_service(AsyncMock())
    result = asyncio.run(service.get_location_name(45.50, None))
    assert result == ""


def test_get_location_name_swallows_exception_and_returns_empty_string():
    gateway = AsyncMock()
    gateway.reverse_geocode.side_effect = RuntimeError("network error")
    service = _make_service(gateway)
    result = asyncio.run(service.get_location_name(45.50, -73.57))
    assert result == ""


def test_get_location_name_returns_empty_string_on_falsy_result():
    gateway = AsyncMock()
    gateway.reverse_geocode.return_value = None
    service = _make_service(gateway)
    result = asyncio.run(service.get_location_name(45.50, -73.57))
    assert result == ""


def test_get_location_name_returns_location_string():
    gateway = AsyncMock()
    gateway.reverse_geocode.return_value = "Montréal, Québec"
    service = _make_service(gateway)
    result = asyncio.run(service.get_location_name(45.50, -73.57))
    assert result == "Montréal, Québec"


# ---------------------------------------------------------------------------
# geocode_for_settings
# ---------------------------------------------------------------------------


def test_geocode_for_settings_returns_not_found_tuple_when_no_result():
    gateway = AsyncMock()
    gateway.geocode_location.return_value = None
    service = _make_service(gateway)
    lat, lon, name = asyncio.run(service.geocode_for_settings("nowhere"))

    assert lat is None
    assert lon is None
    assert name == "Location not found"


def test_geocode_for_settings_returns_coordinates_and_name():
    gateway = AsyncMock()
    gateway.geocode_location.return_value = {
        "lat": 48.8566,
        "lon": 2.3522,
        "name": "Paris, France",
    }
    service = _make_service(gateway)
    lat, lon, name = asyncio.run(service.geocode_for_settings("Paris"))

    assert lat == 48.8566
    assert lon == 2.3522
    assert name == "Paris, France"
