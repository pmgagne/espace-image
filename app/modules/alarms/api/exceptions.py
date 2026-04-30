"""Alarms module exceptions."""


class AlarmsModuleError(Exception):
    """Base exception for alarms module errors."""

    pass


class AlarmNotFoundError(AlarmsModuleError):
    """Raised when an alarm is not found."""

    pass
