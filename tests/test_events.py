"""Tests for shared.wall_common.events module."""

from datetime import datetime
from decimal import Decimal

import pytest

from shared.wall_common.events import (
    EVENT_TYPES,
    BaseEvent,
    ProfileCreated,
    ProfileUpdated,
    SimulationProgress,
    deserialize_event,
)


class TestBaseEvent:
    """Test BaseEvent class."""

    def test_base_event_with_defaults(self):
        """Test BaseEvent with auto-generated fields."""
        event = BaseEvent(
            event_id="", timestamp=None, event_type="TestEvent"  # type: ignore
        )

        # Should auto-generate event_id and timestamp
        assert event.event_id != ""
        assert isinstance(event.timestamp, datetime)
        assert event.event_type == "TestEvent"

    def test_base_event_with_explicit_values(self):
        """Test BaseEvent with explicit values."""
        event_id = "test-event-123"
        timestamp = datetime(2024, 1, 1, 12, 0, 0)

        event = BaseEvent(
            event_id=event_id, timestamp=timestamp, event_type="TestEvent"
        )

        assert event.event_id == event_id
        assert event.timestamp == timestamp
        assert event.event_type == "TestEvent"


class TestProfileCreated:
    """Test ProfileCreated event."""

    @pytest.fixture
    def sample_event(self):
        """Sample ProfileCreated event."""
        return ProfileCreated(
            event_id="profile-created-123",
            timestamp=datetime(2024, 1, 1, 12, 0, 0),
            event_type="ProfileCreated",
            profile_id="wall-001",
            name="Test Wall",
            height=Decimal("100"),
            length=Decimal("200"),
            width=Decimal("5"),
            ice_thickness=Decimal("2.5"),
            created_by="test-user",
        )

    def test_profile_created_initialization(self, sample_event):
        """Test ProfileCreated event initialization."""
        assert sample_event.event_type == "ProfileCreated"
        assert sample_event.profile_id == "wall-001"
        assert sample_event.name == "Test Wall"
        assert sample_event.height == Decimal("100")
        assert sample_event.length == Decimal("200")
        assert sample_event.width == Decimal("5")
        assert sample_event.ice_thickness == Decimal("2.5")
        assert sample_event.created_by == "test-user"

    def test_profile_created_auto_event_type(self):
        """Test that event_type is auto-set."""
        event = ProfileCreated(
            event_id="test",
            timestamp=datetime.now(),
            event_type="",  # Should be overridden
            profile_id="wall-001",
            name="Test Wall",
            height=Decimal("100"),
            length=Decimal("200"),
            width=Decimal("5"),
            ice_thickness=Decimal("2.5"),
        )

        assert event.event_type == "ProfileCreated"

    def test_profile_created_to_dict(self, sample_event):
        """Test ProfileCreated serialization to dict."""
        data = sample_event.to_dict()

        expected = {
            "event_id": "profile-created-123",
            "timestamp": "2024-01-01T12:00:00",
            "event_type": "ProfileCreated",
            "profile_id": "wall-001",
            "name": "Test Wall",
            "height": "100",
            "length": "200",
            "width": "5",
            "ice_thickness": "2.5",
            "created_by": "test-user",
        }

        assert data == expected

    def test_profile_created_from_dict(self, sample_event):
        """Test ProfileCreated deserialization from dict."""
        data = sample_event.to_dict()
        restored_event = ProfileCreated.from_dict(data)

        assert restored_event.event_id == sample_event.event_id
        assert restored_event.timestamp == sample_event.timestamp
        assert restored_event.event_type == sample_event.event_type
        assert restored_event.profile_id == sample_event.profile_id
        assert restored_event.name == sample_event.name
        assert restored_event.height == sample_event.height
        assert restored_event.length == sample_event.length
        assert restored_event.width == sample_event.width
        assert restored_event.ice_thickness == sample_event.ice_thickness
        assert restored_event.created_by == sample_event.created_by

    def test_profile_created_without_created_by(self):
        """Test ProfileCreated without optional created_by field."""
        event = ProfileCreated(
            event_id="test",
            timestamp=datetime.now(),
            event_type="ProfileCreated",
            profile_id="wall-001",
            name="Test Wall",
            height=Decimal("100"),
            length=Decimal("200"),
            width=Decimal("5"),
            ice_thickness=Decimal("2.5"),
        )

        assert event.created_by is None

        data = event.to_dict()
        assert data["created_by"] is None

        restored = ProfileCreated.from_dict(data)
        assert restored.created_by is None


class TestProfileUpdated:
    """Test ProfileUpdated event."""

    @pytest.fixture
    def sample_event(self):
        """Sample ProfileUpdated event."""
        return ProfileUpdated(
            event_id="profile-updated-123",
            timestamp=datetime(2024, 1, 1, 12, 0, 0),
            event_type="ProfileUpdated",
            profile_id="wall-001",
            name="Updated Wall",
            height=Decimal("150"),
            updated_by="test-user",
        )

    def test_profile_updated_initialization(self, sample_event):
        """Test ProfileUpdated event initialization."""
        assert sample_event.event_type == "ProfileUpdated"
        assert sample_event.profile_id == "wall-001"
        assert sample_event.name == "Updated Wall"
        assert sample_event.height == Decimal("150")
        assert sample_event.length is None
        assert sample_event.width is None
        assert sample_event.ice_thickness is None
        assert sample_event.updated_by == "test-user"

    def test_profile_updated_to_dict(self, sample_event):
        """Test ProfileUpdated serialization to dict."""
        data = sample_event.to_dict()

        expected = {
            "event_id": "profile-updated-123",
            "timestamp": "2024-01-01T12:00:00",
            "event_type": "ProfileUpdated",
            "profile_id": "wall-001",
            "name": "Updated Wall",
            "height": "150",
            "length": None,
            "width": None,
            "ice_thickness": None,
            "updated_by": "test-user",
        }

        assert data == expected

    def test_profile_updated_from_dict(self, sample_event):
        """Test ProfileUpdated deserialization from dict."""
        data = sample_event.to_dict()
        restored_event = ProfileUpdated.from_dict(data)

        assert restored_event.event_id == sample_event.event_id
        assert restored_event.profile_id == sample_event.profile_id
        assert restored_event.name == sample_event.name
        assert restored_event.height == sample_event.height
        assert restored_event.length is None
        assert restored_event.width is None
        assert restored_event.ice_thickness is None
        assert restored_event.updated_by == sample_event.updated_by


class TestSimulationProgress:
    """Test SimulationProgress event."""

    @pytest.fixture
    def sample_event(self):
        """Sample SimulationProgress event."""
        return SimulationProgress(
            event_id="sim-progress-123",
            timestamp=datetime(2024, 1, 1, 12, 0, 0),
            event_type="SimulationProgress",
            profile_id="wall-001",
            day=1,
            ice_volume=Decimal("1000.50"),
            manpower_hours=Decimal("500.25"),
            material_cost=Decimal("2501.25"),
            labor_cost=Decimal("7503.75"),
            total_cost=Decimal("10005.00"),
            cumulative_cost=Decimal("10005.00"),
        )

    def test_simulation_progress_initialization(self, sample_event):
        """Test SimulationProgress event initialization."""
        assert sample_event.event_type == "SimulationProgress"
        assert sample_event.profile_id == "wall-001"
        assert sample_event.day == 1
        assert sample_event.ice_volume == Decimal("1000.50")
        assert sample_event.manpower_hours == Decimal("500.25")
        assert sample_event.material_cost == Decimal("2501.25")
        assert sample_event.labor_cost == Decimal("7503.75")
        assert sample_event.total_cost == Decimal("10005.00")
        assert sample_event.cumulative_cost == Decimal("10005.00")

    def test_simulation_progress_to_dict(self, sample_event):
        """Test SimulationProgress serialization to dict."""
        data = sample_event.to_dict()

        expected = {
            "event_id": "sim-progress-123",
            "timestamp": "2024-01-01T12:00:00",
            "event_type": "SimulationProgress",
            "profile_id": "wall-001",
            "day": 1,
            "ice_volume": "1000.50",
            "manpower_hours": "500.25",
            "material_cost": "2501.25",
            "labor_cost": "7503.75",
            "total_cost": "10005.00",
            "cumulative_cost": "10005.00",
        }

        assert data == expected

    def test_simulation_progress_from_dict(self, sample_event):
        """Test SimulationProgress deserialization from dict."""
        data = sample_event.to_dict()
        restored_event = SimulationProgress.from_dict(data)

        assert restored_event.event_id == sample_event.event_id
        assert restored_event.profile_id == sample_event.profile_id
        assert restored_event.day == sample_event.day
        assert restored_event.ice_volume == sample_event.ice_volume
        assert restored_event.manpower_hours == sample_event.manpower_hours
        assert restored_event.material_cost == sample_event.material_cost
        assert restored_event.labor_cost == sample_event.labor_cost
        assert restored_event.total_cost == sample_event.total_cost
        assert restored_event.cumulative_cost == sample_event.cumulative_cost


class TestEventDeserialization:
    """Test event deserialization utilities."""

    def test_event_types_registry(self):
        """Test that all event types are registered."""
        assert "ProfileCreated" in EVENT_TYPES
        assert "ProfileUpdated" in EVENT_TYPES
        assert "SimulationProgress" in EVENT_TYPES
        assert EVENT_TYPES["ProfileCreated"] == ProfileCreated
        assert EVENT_TYPES["ProfileUpdated"] == ProfileUpdated
        assert EVENT_TYPES["SimulationProgress"] == SimulationProgress

    def test_deserialize_profile_created(self):
        """Test deserializing ProfileCreated event."""
        data = {
            "event_id": "test-id",
            "timestamp": "2024-01-01T12:00:00",
            "event_type": "ProfileCreated",
            "profile_id": "wall-001",
            "name": "Test Wall",
            "height": "100",
            "length": "200",
            "width": "5",
            "ice_thickness": "2.5",
            "created_by": None,
        }

        event = deserialize_event(data)

        assert isinstance(event, ProfileCreated)
        assert event.profile_id == "wall-001"
        assert event.name == "Test Wall"
        assert event.height == Decimal("100")

    def test_deserialize_profile_updated(self):
        """Test deserializing ProfileUpdated event."""
        data = {
            "event_id": "test-id",
            "timestamp": "2024-01-01T12:00:00",
            "event_type": "ProfileUpdated",
            "profile_id": "wall-001",
            "name": "Updated Wall",
            "height": "150",
            "length": None,
            "width": None,
            "ice_thickness": None,
            "updated_by": "user123",
        }

        event = deserialize_event(data)

        assert isinstance(event, ProfileUpdated)
        assert event.profile_id == "wall-001"
        assert event.name == "Updated Wall"
        assert event.height == Decimal("150")
        assert event.length is None

    def test_deserialize_simulation_progress(self):
        """Test deserializing SimulationProgress event."""
        data = {
            "event_id": "test-id",
            "timestamp": "2024-01-01T12:00:00",
            "event_type": "SimulationProgress",
            "profile_id": "wall-001",
            "day": 5,
            "ice_volume": "1000.00",
            "manpower_hours": "500.00",
            "material_cost": "2500.00",
            "labor_cost": "7500.00",
            "total_cost": "10000.00",
            "cumulative_cost": "50000.00",
        }

        event = deserialize_event(data)

        assert isinstance(event, SimulationProgress)
        assert event.profile_id == "wall-001"
        assert event.day == 5
        assert event.ice_volume == Decimal("1000.00")
        assert event.cumulative_cost == Decimal("50000.00")

    def test_deserialize_unknown_event_type(self):
        """Test deserializing unknown event type raises error."""
        data = {
            "event_id": "test-id",
            "timestamp": "2024-01-01T12:00:00",
            "event_type": "UnknownEvent",
        }

        with pytest.raises(ValueError, match="Unknown event type: UnknownEvent"):
            deserialize_event(data)

    def test_deserialize_missing_event_type(self):
        """Test deserializing with missing event_type raises error."""
        data = {
            "event_id": "test-id",
            "timestamp": "2024-01-01T12:00:00",
        }

        with pytest.raises(ValueError, match="Unknown event type: None"):
            deserialize_event(data)


class TestEventRoundTrip:
    """Test event serialization/deserialization round trips."""

    def test_profile_created_round_trip(self):
        """Test ProfileCreated serialization round trip."""
        original = ProfileCreated(
            event_id="test-id",
            timestamp=datetime(2024, 1, 1, 12, 0, 0),
            event_type="ProfileCreated",
            profile_id="wall-001",
            name="Test Wall",
            height=Decimal("100.50"),
            length=Decimal("200.75"),
            width=Decimal("5.25"),
            ice_thickness=Decimal("2.33"),
            created_by="test-user",
        )

        # Serialize to dict
        data = original.to_dict()

        # Deserialize using generic deserializer
        restored = deserialize_event(data)

        assert isinstance(restored, ProfileCreated)
        assert restored.event_id == original.event_id
        assert restored.timestamp == original.timestamp
        assert restored.profile_id == original.profile_id
        assert restored.name == original.name
        assert restored.height == original.height
        assert restored.length == original.length
        assert restored.width == original.width
        assert restored.ice_thickness == original.ice_thickness
        assert restored.created_by == original.created_by

    def test_simulation_progress_round_trip(self):
        """Test SimulationProgress serialization round trip."""
        original = SimulationProgress(
            event_id="test-id",
            timestamp=datetime(2024, 1, 1, 12, 0, 0),
            event_type="SimulationProgress",
            profile_id="wall-001",
            day=10,
            ice_volume=Decimal("12345.67"),
            manpower_hours=Decimal("6172.84"),
            material_cost=Decimal("30864.18"),
            labor_cost=Decimal("92592.60"),
            total_cost=Decimal("123456.78"),
            cumulative_cost=Decimal("987654.32"),
        )

        # Serialize to dict
        data = original.to_dict()

        # Deserialize using generic deserializer
        restored = deserialize_event(data)

        assert isinstance(restored, SimulationProgress)
        assert restored.event_id == original.event_id
        assert restored.day == original.day
        assert restored.ice_volume == original.ice_volume
        assert restored.cumulative_cost == original.cumulative_cost
