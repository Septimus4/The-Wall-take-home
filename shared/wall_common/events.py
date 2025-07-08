"""Event models for the Wall system."""

import uuid
from dataclasses import dataclass
from datetime import UTC, datetime
from decimal import Decimal
from typing import Any, TypeVar

T = TypeVar("T", bound="BaseEvent")


@dataclass
class BaseEvent:
    """Base event with common fields."""

    event_id: str
    timestamp: datetime
    event_type: str

    def __post_init__(self) -> None:
        if not self.event_id:
            self.event_id = str(uuid.uuid4())
        if not self.timestamp:
            self.timestamp = datetime.now(UTC)

    @classmethod
    def from_dict(cls: type[T], data: dict[str, Any]) -> T:
        """Base method that should be overridden by subclasses."""
        raise NotImplementedError("Subclasses must implement from_dict")

    def to_dict(self) -> dict[str, Any]:
        """Base method that should be overridden by subclasses."""
        raise NotImplementedError("Subclasses must implement to_dict")


@dataclass
class ProfileCreated(BaseEvent):
    """Event published when a new wall profile is created."""

    profile_id: str
    name: str
    height: Decimal
    length: Decimal
    width: Decimal
    ice_thickness: Decimal
    created_by: str | None = None

    def __post_init__(self) -> None:
        super().__post_init__()
        self.event_type = "ProfileCreated"

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            "event_id": self.event_id,
            "timestamp": self.timestamp.isoformat(),
            "event_type": self.event_type,
            "profile_id": self.profile_id,
            "name": self.name,
            "height": str(self.height),
            "length": str(self.length),
            "width": str(self.width),
            "ice_thickness": str(self.ice_thickness),
            "created_by": self.created_by,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "ProfileCreated":
        """Create from dictionary."""
        return cls(
            event_id=data["event_id"],
            timestamp=datetime.fromisoformat(data["timestamp"]),
            event_type=data["event_type"],
            profile_id=data["profile_id"],
            name=data["name"],
            height=Decimal(data["height"]),
            length=Decimal(data["length"]),
            width=Decimal(data["width"]),
            ice_thickness=Decimal(data["ice_thickness"]),
            created_by=data.get("created_by"),
        )


@dataclass
class ProfileUpdated(BaseEvent):
    """Event published when a wall profile is updated."""

    profile_id: str
    name: str | None = None
    height: Decimal | None = None
    length: Decimal | None = None
    width: Decimal | None = None
    ice_thickness: Decimal | None = None
    updated_by: str | None = None

    def __post_init__(self) -> None:
        super().__post_init__()
        self.event_type = "ProfileUpdated"

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            "event_id": self.event_id,
            "timestamp": self.timestamp.isoformat(),
            "event_type": self.event_type,
            "profile_id": self.profile_id,
            "name": self.name,
            "height": str(self.height) if self.height else None,
            "length": str(self.length) if self.length else None,
            "width": str(self.width) if self.width else None,
            "ice_thickness": str(self.ice_thickness) if self.ice_thickness else None,
            "updated_by": self.updated_by,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "ProfileUpdated":
        """Create from dictionary."""
        return cls(
            event_id=data["event_id"],
            timestamp=datetime.fromisoformat(data["timestamp"]),
            event_type=data["event_type"],
            profile_id=data["profile_id"],
            name=data.get("name"),
            height=Decimal(data["height"]) if data.get("height") else None,
            length=Decimal(data["length"]) if data.get("length") else None,
            width=Decimal(data["width"]) if data.get("width") else None,
            ice_thickness=Decimal(data["ice_thickness"])
            if data.get("ice_thickness")
            else None,
            updated_by=data.get("updated_by"),
        )


@dataclass
class SimulationProgress(BaseEvent):
    """Event published with daily simulation progress."""

    profile_id: str
    day: int
    ice_volume: Decimal
    manpower_hours: Decimal
    material_cost: Decimal
    labor_cost: Decimal
    total_cost: Decimal
    cumulative_cost: Decimal

    def __post_init__(self) -> None:
        super().__post_init__()
        self.event_type = "SimulationProgress"

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            "event_id": self.event_id,
            "timestamp": self.timestamp.isoformat(),
            "event_type": self.event_type,
            "profile_id": self.profile_id,
            "day": self.day,
            "ice_volume": str(self.ice_volume),
            "manpower_hours": str(self.manpower_hours),
            "material_cost": str(self.material_cost),
            "labor_cost": str(self.labor_cost),
            "total_cost": str(self.total_cost),
            "cumulative_cost": str(self.cumulative_cost),
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "SimulationProgress":
        """Create from dictionary."""
        return cls(
            event_id=data["event_id"],
            timestamp=datetime.fromisoformat(data["timestamp"]),
            event_type=data["event_type"],
            profile_id=data["profile_id"],
            day=data["day"],
            ice_volume=Decimal(data["ice_volume"]),
            manpower_hours=Decimal(data["manpower_hours"]),
            material_cost=Decimal(data["material_cost"]),
            labor_cost=Decimal(data["labor_cost"]),
            total_cost=Decimal(data["total_cost"]),
            cumulative_cost=Decimal(data["cumulative_cost"]),
        )


# Event type registry for deserialization
EVENT_TYPES: dict[str, type[BaseEvent]] = {
    "ProfileCreated": ProfileCreated,
    "ProfileUpdated": ProfileUpdated,
    "SimulationProgress": SimulationProgress,
}


def deserialize_event(data: dict[str, Any]) -> BaseEvent:
    """Deserialize event from dictionary based on event_type."""
    event_type = data.get("event_type")
    if not event_type or event_type not in EVENT_TYPES:
        raise ValueError(f"Unknown event type: {event_type}")

    event_class = EVENT_TYPES[event_type]
    return event_class.from_dict(data)
