"""REST-only request models for media endpoints."""

from pydantic import BaseModel, Field


class CreatePresetRequest(BaseModel):
    """Request payload for creating a media preset."""

    name: str = Field(min_length=1)
