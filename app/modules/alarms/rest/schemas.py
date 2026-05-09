"""REST-only request models for alarms endpoints."""

from pydantic import BaseModel, Field


class SimulateAlarmRequest(BaseModel):
    """Request payload for creating a simulated alarm."""

    delay_seconds: int = Field(ge=0)
