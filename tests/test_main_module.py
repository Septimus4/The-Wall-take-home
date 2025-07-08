"""Additional tests for the simulator main module to improve coverage."""

from decimal import Decimal
from unittest.mock import AsyncMock, Mock, patch

import pytest
from fastapi.testclient import TestClient

from services.simulator.main import (
    HealthResponse,
    SimulationRequest,
    app,
    handle_profile_created,
    process_event,
    run_event_consumer,
    run_simulation_for_profile,
)
from shared.wall_common.events import ProfileCreated


class TestMainModule:
    """Test cases for main module functionality."""

    def test_health_response_model(self):
        """Test HealthResponse model creation."""
        response = HealthResponse(
            status="healthy", version="1.0.0", kafka_connected=True
        )
        assert response.status == "healthy"
        assert response.version == "1.0.0"
        assert response.kafka_connected is True

    def test_simulation_request_model(self):
        """Test SimulationRequest model creation."""
        request = SimulationRequest(profile_id="test-id", days=5)
        assert request.profile_id == "test-id"
        assert request.days == 5

    def test_simulation_request_default_days(self):
        """Test SimulationRequest with default days."""
        request = SimulationRequest(profile_id="test-id")
        assert request.profile_id == "test-id"
        assert request.days == 1

    @patch("services.simulator.main.consumer", None)
    @patch("services.simulator.main.producer", None)
    def test_health_check_no_connections(self):
        """Test health check when no connections are established."""
        client = TestClient(app)
        response = client.get("/health")

        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "degraded"
        assert data["kafka_connected"] is False

    @patch("services.simulator.main.producer", None)
    def test_trigger_simulation_no_producer(self):
        """Test simulation trigger when producer is not available."""
        client = TestClient(app)
        response = client.post("/simulate", json={"profile_id": "test-id", "days": 1})

        assert response.status_code == 200
        data = response.json()
        assert "error" in data
        assert data["error"] == "Producer not initialized"

    @patch("services.simulator.main.producer")
    def test_trigger_simulation_success(self, mock_producer):
        """Test successful simulation trigger."""
        mock_producer.is_connected.return_value = True

        client = TestClient(app)
        response = client.post("/simulate", json={"profile_id": "test-id", "days": 3})

        assert response.status_code == 200
        data = response.json()
        assert "message" in data
        assert "test-id" in data["message"]
        assert data["days"] == 3

    @pytest.mark.asyncio
    async def test_process_event_profile_created(self):
        """Test processing ProfileCreated event."""
        from datetime import UTC, datetime

        event = ProfileCreated(
            event_id="test-id",
            timestamp=datetime.now(UTC),
            event_type="ProfileCreated",
            profile_id="profile-123",
            name="Test Wall",
            height=Decimal("10.0"),
            length=Decimal("100.0"),
            width=Decimal("2.0"),
            ice_thickness=Decimal("0.5"),
            created_by="test-user",
        )

        with patch("services.simulator.main.handle_profile_created") as mock_handle:
            await process_event(event)
            mock_handle.assert_called_once_with(event)

    @pytest.mark.asyncio
    async def test_process_event_unknown_type(self):
        """Test processing unknown event type."""
        mock_event = Mock()
        mock_event.event_type = "UnknownEvent"
        mock_event.event_id = "test-id"

        # Should not raise exception, just log and ignore
        await process_event(mock_event)

    @pytest.mark.asyncio
    async def test_handle_profile_created(self):
        """Test handling ProfileCreated event."""
        from datetime import UTC, datetime

        event = ProfileCreated(
            event_id="test-id",
            timestamp=datetime.now(UTC),
            event_type="ProfileCreated",
            profile_id="profile-123",
            name="Test Wall",
            height=Decimal("10.0"),
            length=Decimal("100.0"),
            width=Decimal("2.0"),
            ice_thickness=Decimal("0.5"),
            created_by="test-user",
        )

        with patch(
            "services.simulator.main.run_simulation_for_profile"
        ) as mock_run_sim, patch("services.simulator.main.config") as mock_config:
            mock_config.initial_simulation_days = 3

            await handle_profile_created(event)

            mock_run_sim.assert_called_once_with("profile-123", 3, event)

    @pytest.mark.asyncio
    async def test_run_simulation_for_profile_no_producer(self):
        """Test simulation when producer is not available."""
        with patch("services.simulator.main.producer", None):
            await run_simulation_for_profile("test-id", 1)
            # Should not raise exception, just log error

    @pytest.mark.asyncio
    async def test_run_simulation_for_profile_no_profile_event(self):
        """Test simulation when profile event is not provided."""
        mock_producer = Mock()
        with patch("services.simulator.main.producer", mock_producer):
            await run_simulation_for_profile("test-id", 1, None)
            # Should not raise exception, just log warning

    @pytest.mark.asyncio
    async def test_run_simulation_for_profile_success(self):
        """Test successful simulation run."""
        from datetime import UTC, datetime

        # Create profile event
        profile_event = ProfileCreated(
            event_id="test-id",
            timestamp=datetime.now(UTC),
            event_type="ProfileCreated",
            profile_id="profile-123",
            name="Test Wall",
            height=Decimal("10.0"),
            length=Decimal("100.0"),
            width=Decimal("2.0"),
            ice_thickness=Decimal("0.5"),
            created_by="test-user",
        )

        # Mock producer
        mock_producer = AsyncMock()

        with patch("services.simulator.main.producer", mock_producer):
            await run_simulation_for_profile("profile-123", 2, profile_event)

            # Should have published 2 simulation progress events
            assert mock_producer.publish_event.call_count == 2

    @pytest.mark.asyncio
    async def test_run_simulation_for_profile_exception(self):
        """Test simulation with exception during processing."""
        from datetime import UTC, datetime

        profile_event = ProfileCreated(
            event_id="test-id",
            timestamp=datetime.now(UTC),
            event_type="ProfileCreated",
            profile_id="profile-123",
            name="Test Wall",
            height=Decimal("10.0"),
            length=Decimal("100.0"),
            width=Decimal("2.0"),
            ice_thickness=Decimal("0.5"),
            created_by="test-user",
        )

        mock_producer = AsyncMock()
        mock_producer.publish_event.side_effect = Exception("Publish failed")

        with patch("services.simulator.main.producer", mock_producer), pytest.raises(
            Exception, match="Publish failed"
        ):
            await run_simulation_for_profile("profile-123", 1, profile_event)

    @pytest.mark.asyncio
    async def test_run_event_consumer_no_consumer(self):
        """Test event consumer when consumer is not initialized."""
        with patch("services.simulator.main.consumer", None):
            await run_event_consumer()
            # Should not raise exception, just log error


class TestMockEventInjection:
    """Test cases for mock event injection endpoint."""

    def test_inject_profile_created_not_mock_consumer(self):
        """Test mock event injection with non-mock consumer."""
        # Consumer is not MockKafkaEventConsumer
        client = TestClient(app)
        response = client.post(
            "/test/inject-profile-created",
            json={
                "profile_id": "test-123",
                "name": "Test Wall",
                "height": 10.0,
                "length": 100.0,
                "width": 2.0,
                "ice_thickness": 0.5,
            },
        )

        assert response.status_code == 200
        data = response.json()
        assert "error" in data
        assert "mock Kafka implementation" in data["error"]
