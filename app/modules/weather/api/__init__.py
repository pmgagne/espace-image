"""Public weather module API."""

from .interfaces import (
    IWeatherService,
    WeatherData,
    WeatherLocationResult,
    get_weather_service,
)

__all__ = [
    "IWeatherService",
    "WeatherData",
    "WeatherLocationResult",
    "get_weather_service",
]

from app.modules.weather.internal.infrastructure.presenter import render_weather_fragment

__all__.append("render_weather_fragment")
