"""Transport-agnostic DTOs for alarms module."""

from .contracts import AlarmEventDTO
from .dtos import AlarmData, AlarmEventData

__all__ = ["AlarmData", "AlarmEventDTO", "AlarmEventData"]
