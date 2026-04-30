"""Weather module exceptions."""


class WeatherModuleError(Exception):
    """Base exception for weather module public API."""


class WeatherProviderError(WeatherModuleError):
    """Raised when a weather/geocoding provider cannot be reached reliably."""
