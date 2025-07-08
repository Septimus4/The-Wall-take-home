"""
Common utilities for The Wall project.
"""

import logging
from typing import Any

logger = logging.getLogger(__name__)


def log_event(event_name: str, data: dict[str, Any]) -> None:
    """Log an event with structured data."""
    logger.info(f"Event: {event_name}", extra={"event_data": data})


def validate_positive_number(value: float, field_name: str) -> None:
    """Validate that a number is positive."""
    if value <= 0:
        raise ValueError(f"{field_name} must be positive, got {value}")
