"""Tests for WeatherService HTTP fetch and parsing logic.

WeatherService builds an httpx.AsyncClient inline in each static method, so
tests mock the class via patch() to avoid real network calls.  The fake
async-context-manager pattern used here mirrors the one the production code
requires.
"""

import asyncio
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.modules.weather.internal.infrastructure.weather_api import WeatherService

_PATCH_TARGET = "app.modules.weather.internal.infrastructure.weather_api.httpx.AsyncClient"


def _mock_http(json_data: dict) -> tuple[MagicMock, AsyncMock]:
    """Build a fake httpx.AsyncClient context-manager.

    Returns:
        (client_cm, mock_client) — patch AsyncClient with return_value=client_cm
        and inspect mock_client.get.call_args to verify request details.
    """
    mock_response = MagicMock()
    mock_response.raise_for_status = MagicMock()
    mock_response.json.return_value = json_data

    mock_client = AsyncMock()
    mock_client.get = AsyncMock(return_value=mock_response)

    client_cm = MagicMock()
    client_cm.__aenter__ = AsyncMock(return_value=mock_client)
    client_cm.__aexit__ = AsyncMock(return_value=None)

    return client_cm, mock_client


# ---------------------------------------------------------------------------
# get_current_weather — WMO code mapping
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "code,expected_condition",
    [
        (0, "Ciel dégagé"),
        (61, "Pluie légère"),
        (95, "Orage"),
        (999, "Inconnu"),  # unknown code falls back to "Inconnu"
    ],
)
def test_get_current_weather_maps_wmo_codes(code, expected_condition):
    client_cm, _ = _mock_http({"current_weather": {"temperature": 15.7, "weathercode": code}})

    with patch(_PATCH_TARGET, return_value=client_cm):
        result = asyncio.run(WeatherService.get_current_weather(45.50, -73.57))

    assert result["condition"] == expected_condition


def test_get_current_weather_rounds_temperature():
    client_cm, _ = _mock_http({"current_weather": {"temperature": 17.8, "weathercode": 0}})

    with patch(_PATCH_TARGET, return_value=client_cm):
        result = asyncio.run(WeatherService.get_current_weather(45.50, -73.57))

    assert result["temp"] == round(17.8)


def test_get_current_weather_formats_location_string():
    client_cm, _ = _mock_http({"current_weather": {"temperature": 10.0, "weathercode": 0}})

    with patch(_PATCH_TARGET, return_value=client_cm):
        result = asyncio.run(WeatherService.get_current_weather(45.5017, -73.5673))

    assert result["location"] == "45.50, -73.57"


def test_get_current_weather_returns_dash_on_missing_temperature():
    # API may omit temperature in error responses
    client_cm, _ = _mock_http({"current_weather": {"weathercode": 0}})

    with patch(_PATCH_TARGET, return_value=client_cm):
        result = asyncio.run(WeatherService.get_current_weather(0.0, 0.0))

    assert result["temp"] == "--"


def test_get_current_weather_returns_error_fallback_on_exception():
    with patch(_PATCH_TARGET, side_effect=RuntimeError("network error")):
        result = asyncio.run(WeatherService.get_current_weather(0.0, 0.0))

    assert result == {"temp": "--", "condition": "Service Error", "location": "Unavailable"}


# ---------------------------------------------------------------------------
# geocode_location
# ---------------------------------------------------------------------------


def test_geocode_location_maps_first_result():
    payload = {
        "results": [
            {"latitude": 48.8566, "longitude": 2.3522, "name": "Paris", "country": "France"}
        ]
    }
    client_cm, _ = _mock_http(payload)

    with patch(_PATCH_TARGET, return_value=client_cm):
        result = asyncio.run(WeatherService.geocode_location("Paris"))

    assert result == {"lat": 48.8566, "lon": 2.3522, "name": "Paris, France"}


def test_geocode_location_returns_none_when_results_empty():
    client_cm, _ = _mock_http({"results": []})

    with patch(_PATCH_TARGET, return_value=client_cm):
        result = asyncio.run(WeatherService.geocode_location("nowhere"))

    assert result is None


def test_geocode_location_returns_none_when_results_key_absent():
    client_cm, _ = _mock_http({})

    with patch(_PATCH_TARGET, return_value=client_cm):
        result = asyncio.run(WeatherService.geocode_location("nowhere"))

    assert result is None


def test_geocode_location_returns_none_on_exception():
    with patch(_PATCH_TARGET, side_effect=RuntimeError("timeout")):
        result = asyncio.run(WeatherService.geocode_location("Paris"))

    assert result is None


# ---------------------------------------------------------------------------
# reverse_geocode — label assembly and User-Agent header
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "address,expected",
    [
        ({"city": "Montréal", "state": "Québec"}, "Montréal, Québec"),
        ({"town": "Verdun", "state": "Québec"}, "Verdun, Québec"),
        ({"village": "Saint-Lin", "region": "Lanaudière"}, "Saint-Lin, Lanaudière"),
        ({"city": "Montréal"}, "Montréal"),  # state absent → city only
        ({"state": "Québec"}, "Québec"),  # city absent → state only
    ],
)
def test_reverse_geocode_builds_location_label(address, expected):
    client_cm, _ = _mock_http({"address": address})

    with patch(_PATCH_TARGET, return_value=client_cm):
        result = asyncio.run(WeatherService.reverse_geocode(45.50, -73.57))

    assert result == expected


def test_reverse_geocode_sends_user_agent_header():
    """Nominatim requires a User-Agent header — verify it is sent."""
    client_cm, mock_client = _mock_http({"address": {"city": "Montréal", "state": "Québec"}})

    with patch(_PATCH_TARGET, return_value=client_cm):
        asyncio.run(WeatherService.reverse_geocode(45.50, -73.57))

    _, kwargs = mock_client.get.call_args
    assert kwargs.get("headers") == {"User-Agent": "Espace-Image/1.0"}


def test_reverse_geocode_returns_none_on_exception():
    with patch(_PATCH_TARGET, side_effect=RuntimeError("DNS failure")):
        result = asyncio.run(WeatherService.reverse_geocode(0.0, 0.0))

    assert result is None
