from dataclasses import dataclass

from app.main import app as fastapi_app
from app.modules.slideshow.api.interfaces import get_slideshow_service
from app.modules.weather.api.interfaces import get_weather_service


@dataclass
class _FakeWeatherData:
    temp: int | str
    condition: str
    location: str


@dataclass
class _FakeWeatherLocationResult:
    lat: float
    lon: float
    name: str


@dataclass
class _FakeSlideSelection:
    img_url: str | None
    error_msg: str | None


class _FakeWeatherService:
    async def get_current_weather(self, lat: float, lon: float):
        return _FakeWeatherData(temp=21, condition="sunny", location=f"{lat},{lon}")

    async def geocode_location(self, query: str):
        return _FakeWeatherLocationResult(lat=45.5, lon=-73.6, name=f"resolved:{query}")

    async def reverse_geocode(self, lat: float, lon: float):
        return f"rev:{lat},{lon}"


class _FakeSlideshowService:
    def select_next_slide(self, mode: str = "modern"):
        return _FakeSlideSelection(img_url=f"/images/{mode}.jpg", error_msg=None)


def test_api_weather_routes_return_json(client):
    fastapi_app.dependency_overrides[get_weather_service] = lambda: _FakeWeatherService()
    try:
        current = client.get("/api/v1/weather/current?lat=45.5&lon=-73.6")
        assert current.status_code == 200
        assert current.headers["content-type"].startswith("application/json")
        assert current.json()["condition"] == "sunny"

        location_name = client.get("/api/v1/weather/location-name?lat=45.5&lon=-73.6")
        assert location_name.status_code == 200
        assert location_name.headers["content-type"].startswith("application/json")
        assert location_name.json()["name"] == "rev:45.5,-73.6"

        geocode = client.get("/api/v1/weather/geocode?q=Montreal")
        assert geocode.status_code == 200
        assert geocode.headers["content-type"].startswith("application/json")
        assert geocode.json()["name"] == "resolved:Montreal"
    finally:
        fastapi_app.dependency_overrides.pop(get_weather_service, None)


def test_api_slideshow_routes_return_json(client):
    fastapi_app.dependency_overrides[get_slideshow_service] = lambda: _FakeSlideshowService()
    try:
        current = client.get("/api/v1/slideshow/current?mode=modern")
        assert current.status_code == 200
        assert current.headers["content-type"].startswith("application/json")
        assert current.json()["img_url"] == "/images/modern.jpg"

        next_slide = client.get("/api/v1/slideshow/next?mode=legacy")
        assert next_slide.status_code == 200
        assert next_slide.headers["content-type"].startswith("application/json")
        assert next_slide.json()["img_url"] == "/images/legacy.jpg"
    finally:
        fastapi_app.dependency_overrides.pop(get_slideshow_service, None)
