from pydantic import BaseModel


class WeatherResponse(BaseModel):
    """Structured weather response used for API documentation."""

    temp: float | None
    condition: str | None
    location: str | None = None


class SlideResponse(BaseModel):
    """Slide fragment response model for documentation purposes."""

    img_url: str | None
    error_msg: str | None = None


class AlarmContextItem(BaseModel):
    uid: str
    name: str
    fallback_text: str | None
    start_iso: str | None
    end_iso: str | None
    all_day: bool | None
    mock: bool | None
