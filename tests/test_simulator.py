# tests/test_simulator.py
# mypy: ignore-errors
"""Tests for the simulation service."""

from datetime import UTC, datetime
from decimal import Decimal

import pytest

import services.simulator.main
from services.simulator.config import KafkaConfig, SimulatorConfig
from services.simulator.kafka_consumer import KafkaEventConsumer
from services.simulator.kafka_producer import KafkaEventProducer
from services.simulator.main import (
    process_event,
    run_simulation_for_profile,
)
from services.simulator.mock_kafka import MockKafkaEventConsumer, MockKafkaEventProducer
from shared.wall_common.events import ProfileCreated, ProfileUpdated, SimulationProgress


class TestSimulatorConfig:
    """Test configuration classes."""

    def test_kafka_config_defaults(self):
        """Test KafkaConfig default values."""
        config = KafkaConfig()

        assert config.bootstrap_servers == "localhost:9092"
        assert config.consumer_group == "wall-simulator"
        assert config.profile_topic == "wall.profiles"
        assert config.simulation_topic == "wall.simulation"

    def test_simulator_config_defaults(self):
        """Test SimulatorConfig default values."""
        config = SimulatorConfig()

        assert config.version == "0.1.0"
        assert config.environment == "development"
        assert config.initial_simulation_days == 5
        assert isinstance(config.kafka_config, KafkaConfig)


class TestMockKafka:
    """Test mock Kafka implementations."""

    def test_mock_producer_initialization(self):
        """Test mock producer initialization."""
        config = KafkaConfig()
        producer = MockKafkaEventProducer(config)

        assert producer.config == config
        assert producer._published_events == []

    @pytest.mark.asyncio
    async def test_mock_producer_publish_event(self):
        """Test mock producer event publishing."""
        config = KafkaConfig()
        producer = MockKafkaEventProducer(config)

        # Create a test event
        event = ProfileCreated(
            event_id="test-123",
            timestamp=datetime.now(UTC),
            event_type="ProfileCreated",
            profile_id="profile-456",
            name="Test Wall",
            height=Decimal("10.0"),
            length=Decimal("100.0"),
            width=Decimal("5.0"),
            ice_thickness=Decimal("0.5"),
        )

        await producer.publish_event(event)

        published_events = producer.get_published_events()
        assert len(published_events) == 1
        assert published_events[0]["event_type"] == "ProfileCreated"
        assert published_events[0]["profile_id"] == "profile-456"

    @pytest.mark.asyncio
    async def test_mock_consumer_event_flow(self):
        """Test mock consumer event consumption."""
        config = KafkaConfig()
        consumer = MockKafkaEventConsumer(config)

        # Test event data
        test_event = {
            "event_type": "ProfileCreated",
            "profile_id": "test-profile",
            "name": "Test Wall",
        }

        # Add event to queue
        await consumer.add_mock_event(test_event)

        # Consume events
        events_received = []
        async for event in consumer.consume_events():
            events_received.append(event)
            if len(events_received) >= 1:
                break

        assert len(events_received) == 1
        assert events_received[0]["event_type"] == "ProfileCreated"
        assert events_received[0]["profile_id"] == "test-profile"


class TestSimulationLogic:
    """Test simulation business logic."""

    @pytest.mark.asyncio
    async def test_process_profile_created_event(self):
        """Test processing ProfileCreated event."""
        # Create test event
        event = ProfileCreated(
            event_id="test-123",
            timestamp=datetime.now(UTC),
            event_type="ProfileCreated",
            profile_id="profile-456",
            name="Test Wall",
            height=Decimal("5.0"),
            length=Decimal("50.0"),
            width=Decimal("3.0"),
            ice_thickness=Decimal("0.3"),
        )

        # Mock the global producer for testing
        original_producer = services.simulator.main.producer
        mock_producer = MockKafkaEventProducer(KafkaConfig())
        services.simulator.main.producer = mock_producer

        try:
            # Process the event
            await process_event(event)

            # Check that simulation progress events were published
            published_events = mock_producer.get_published_events()

            # Should have published 5 simulation progress events (default initial_simulation_days)
            simulation_events = [
                e for e in published_events if e["event_type"] == "SimulationProgress"
            ]
            assert len(simulation_events) == 5

            # Check first day
            first_day = simulation_events[0]
            assert first_day["profile_id"] == "profile-456"
            assert first_day["day"] == 1
            assert "ice_volume" in first_day
            assert "total_cost" in first_day

            # Check that cumulative cost increases each day
            cumulative_costs = [
                Decimal(e["cumulative_cost"]) for e in simulation_events
            ]
            for i in range(1, len(cumulative_costs)):
                assert cumulative_costs[i] > cumulative_costs[i - 1]

        finally:
            # Restore original producer
            services.simulator.main.producer = original_producer

    @pytest.mark.asyncio
    async def test_run_simulation_for_profile(self):
        """Test running simulation for a specific profile."""
        # Create test profile event
        profile_event = ProfileCreated(
            event_id="test-123",
            timestamp=datetime.now(UTC),
            event_type="ProfileCreated",
            profile_id="profile-789",
            name="Simulation Test Wall",
            height=Decimal("8.0"),
            length=Decimal("120.0"),
            width=Decimal("4.0"),
            ice_thickness=Decimal("0.4"),
        )

        # Mock producer
        mock_producer = MockKafkaEventProducer(KafkaConfig())

        # Mock the global producer
        original_producer = services.simulator.main.producer
        services.simulator.main.producer = mock_producer

        try:
            # Run simulation for 3 days
            await run_simulation_for_profile("profile-789", 3, profile_event)

            # Check published events
            published_events = mock_producer.get_published_events()
            simulation_events = [
                e for e in published_events if e["event_type"] == "SimulationProgress"
            ]

            assert len(simulation_events) == 3

            # Verify day sequence
            days = [e["day"] for e in simulation_events]
            assert days == [1, 2, 3]

            # Verify profile_id consistency
            profile_ids = {e["profile_id"] for e in simulation_events}
            assert profile_ids == {"profile-789"}

        finally:
            # Restore original producer
            services.simulator.main.producer = original_producer

    @pytest.mark.asyncio
    async def test_simulation_with_no_profile_event(self):
        """Test simulation when profile event is not available."""
        mock_producer = MockKafkaEventProducer(KafkaConfig())

        original_producer = services.simulator.main.producer
        services.simulator.main.producer = mock_producer

        try:
            # Run simulation without profile event
            await run_simulation_for_profile("missing-profile", 2, None)

            # Should not publish any events
            published_events = mock_producer.get_published_events()
            assert len(published_events) == 0

        finally:
            services.simulator.main.producer = original_producer


@pytest.mark.asyncio
async def test_simulation_calculations():
    """Test that simulation calculations are correct."""
    from shared.wall_common.calcs import WallProfile, simulate_daily_progress

    # Create test profile
    wall_profile = WallProfile(
        name="Test Wall",
        height=Decimal("10.0"),
        length=Decimal("100.0"),
        width=Decimal("5.0"),
        ice_thickness=Decimal("0.5"),
    )

    # Calculate day 1
    day1_stats = simulate_daily_progress(wall_profile, 1)

    # Expected ice volume = height * length * ice_thickness = 10 * 100 * 0.5 = 500
    expected_ice_volume = Decimal("500.00")
    assert day1_stats.ice_volume == expected_ice_volume

    # Expected manpower hours = ice_volume * 0.5 = 500 * 0.5 = 250
    expected_manpower_hours = Decimal("250.00")
    assert day1_stats.manpower_hours == expected_manpower_hours

    # Expected material cost = ice_volume * 2.5 = 500 * 2.5 = 1250
    expected_material_cost = Decimal("1250.00")
    assert day1_stats.material_cost == expected_material_cost

    # Expected labor cost = manpower_hours * 15 = 250 * 15 = 3750
    expected_labor_cost = Decimal("3750.00")
    assert day1_stats.labor_cost == expected_labor_cost

    # Expected total cost = material_cost + labor_cost = 1250 + 3750 = 5000
    expected_total_cost = Decimal("5000.00")
    assert day1_stats.total_cost == expected_total_cost

    # Day 1 cumulative cost should equal total cost
    assert day1_stats.cumulative_cost == expected_total_cost


class TestKafkaComponents:
    """Test real Kafka components."""

    def test_kafka_consumer_initialization(self):
        """Test KafkaEventConsumer initialization."""
        config = KafkaConfig()
        consumer = KafkaEventConsumer(config)

        assert consumer.config == config
        assert consumer.consumer is None
        assert not consumer._running

    def test_kafka_producer_initialization(self):
        """Test KafkaEventProducer initialization."""
        config = KafkaConfig()
        producer = KafkaEventProducer(config)

        assert producer.config == config
        assert producer.producer is not None  # Should be initialized

    def test_get_topic_for_event_type(self):
        """Test topic mapping logic."""
        config = KafkaConfig()
        producer = KafkaEventProducer(config)

        # Test known event types
        assert (
            producer._get_topic_for_event_type("ProfileCreated") == config.profile_topic
        )
        assert (
            producer._get_topic_for_event_type("ProfileUpdated") == config.profile_topic
        )
        assert (
            producer._get_topic_for_event_type("SimulationProgress")
            == config.simulation_topic
        )

        # Test unknown event type defaults to simulation topic
        assert (
            producer._get_topic_for_event_type("UnknownEvent")
            == config.simulation_topic
        )

    @pytest.mark.asyncio
    async def test_kafka_producer_close(self):
        """Test KafkaEventProducer close method."""
        config = KafkaConfig()
        producer = KafkaEventProducer(config)

        # Should not raise an exception
        await producer.close()
        assert producer.producer is None

    @pytest.mark.asyncio
    async def test_kafka_consumer_close(self):
        """Test KafkaEventConsumer close method."""
        config = KafkaConfig()
        consumer = KafkaEventConsumer(config)

        # Should not raise an exception
        await consumer.close()
        assert not consumer._running
        assert consumer.consumer is None


class TestConfigurationEdgeCases:
    """Test configuration edge cases and customization."""

    def test_kafka_config_with_custom_values(self):
        """Test KafkaConfig with custom values."""
        config = KafkaConfig(
            bootstrap_servers="custom:9092",
            consumer_group="custom-group",
            profile_topic="custom.profiles",
            simulation_topic="custom.simulation",
        )

        assert config.bootstrap_servers == "custom:9092"
        assert config.consumer_group == "custom-group"
        assert config.profile_topic == "custom.profiles"
        assert config.simulation_topic == "custom.simulation"

    def test_simulator_config_with_custom_values(self):
        """Test SimulatorConfig with custom values."""
        config = SimulatorConfig(
            version="1.0.0",
            environment="production",
            initial_simulation_days=10,
            max_simulation_days=500,
        )

        assert config.version == "1.0.0"
        assert config.environment == "production"
        assert config.initial_simulation_days == 10
        assert config.max_simulation_days == 500
        assert isinstance(config.kafka_config, KafkaConfig)

    def test_kafka_config_producer_settings(self):
        """Test KafkaConfig producer-specific settings."""
        config = KafkaConfig()

        assert config.acks == "all"
        assert config.retries == 3
        assert config.batch_size == 16384
        assert config.linger_ms == 10

    def test_kafka_config_consumer_settings(self):
        """Test KafkaConfig consumer-specific settings."""
        config = KafkaConfig()

        assert config.auto_offset_reset == "earliest"
        assert config.enable_auto_commit is True
        assert config.auto_commit_interval_ms == 1000


class TestEventTypes:
    """Test different event types and their handling."""

    @pytest.mark.asyncio
    async def test_profile_updated_event_processing(self):
        """Test processing ProfileUpdated event."""
        # Create test event
        event = ProfileUpdated(
            event_id="test-456",
            timestamp=datetime.now(UTC),
            event_type="ProfileUpdated",
            profile_id="profile-789",
            name="Updated Wall",
            height=Decimal("8.0"),
            length=Decimal("80.0"),
            width=Decimal("4.0"),
            ice_thickness=Decimal("0.4"),
        )

        # Mock producer
        mock_producer = MockKafkaEventProducer(KafkaConfig())
        original_producer = services.simulator.main.producer
        services.simulator.main.producer = mock_producer

        try:
            # Process the event
            await process_event(event)

            # ProfileUpdated events should not trigger simulation, only ProfileCreated events do
            published_events = mock_producer.get_published_events()
            simulation_events = [
                e for e in published_events if e["event_type"] == "SimulationProgress"
            ]

            # Should have published 0 simulation progress events (ProfileUpdated doesn't trigger simulation)
            assert len(simulation_events) == 0

        finally:
            services.simulator.main.producer = original_producer

    @pytest.mark.asyncio
    async def test_mock_kafka_additional_methods(self):
        """Test additional mock Kafka methods."""
        config = KafkaConfig()

        # Test producer
        producer = MockKafkaEventProducer(config)

        # Test is_connected
        is_connected = await producer.is_connected()
        assert is_connected is True

        # Test flush
        await producer.flush()  # Should not raise exception

        # Test clear_published_events
        producer.clear_published_events()
        assert len(producer.get_published_events()) == 0

        # Test close
        await producer.close()  # Should not raise exception

        # Test consumer
        consumer = MockKafkaEventConsumer(config)

        # Test is_connected
        is_connected = await consumer.is_connected()
        assert is_connected is True

        # Test close
        await consumer.close()  # Should not raise exception


class TestMockKafkaAdvanced:
    """Test advanced mock Kafka functionality."""

    @pytest.mark.asyncio
    async def test_mock_consumer_multiple_events(self):
        """Test mock consumer with multiple events."""
        config = KafkaConfig()
        consumer = MockKafkaEventConsumer(config)

        # Add multiple test events
        events_to_add = [
            {"event_type": "ProfileCreated", "profile_id": "profile-1"},
            {"event_type": "ProfileUpdated", "profile_id": "profile-2"},
            {"event_type": "SimulationProgress", "profile_id": "profile-3"},
        ]

        for event in events_to_add:
            await consumer.add_mock_event(event)

        # Consume events
        received_events = []
        async for event in consumer.consume_events():
            received_events.append(event)
            if len(received_events) >= len(events_to_add):
                break

        assert len(received_events) == len(events_to_add)

        # Verify event types
        received_types = [e["event_type"] for e in received_events]
        expected_types = [e["event_type"] for e in events_to_add]
        assert received_types == expected_types

    @pytest.mark.asyncio
    async def test_mock_producer_event_topic_mapping(self):
        """Test mock producer correctly maps events to topics."""
        config = KafkaConfig()
        producer = MockKafkaEventProducer(config)

        # Create different types of events
        profile_event = ProfileCreated(
            event_id="test-1",
            timestamp=datetime.now(UTC),
            event_type="ProfileCreated",
            profile_id="profile-1",
            name="Test Wall",
            height=Decimal("5.0"),
            length=Decimal("50.0"),
            width=Decimal("3.0"),
            ice_thickness=Decimal("0.3"),
        )

        simulation_event = SimulationProgress(
            event_id="test-2",
            timestamp=datetime.now(UTC),
            event_type="SimulationProgress",
            profile_id="profile-1",
            day=1,
            ice_volume=Decimal("75.00"),
            manpower_hours=Decimal("37.50"),
            material_cost=Decimal("187.50"),
            labor_cost=Decimal("562.50"),
            total_cost=Decimal("750.00"),
            cumulative_cost=Decimal("750.00"),
        )

        # Publish events
        await producer.publish_event(profile_event)
        await producer.publish_event(simulation_event)

        # Verify topics are mapped correctly
        published_events = producer.get_published_events()
        assert len(published_events) == 2

        # The actual topic mapping is done in _get_topic_for_event_type
        # which we tested separately, but we can verify the events were published
        profile_events = [
            e for e in published_events if e["event_type"] == "ProfileCreated"
        ]
        simulation_events = [
            e for e in published_events if e["event_type"] == "SimulationProgress"
        ]

        assert len(profile_events) == 1
        assert len(simulation_events) == 1


class TestCLI:
    """Test CLI functionality."""

    def test_cli_imports(self):
        """Test that CLI module can be imported."""
        import services.simulator.cli

        assert hasattr(services.simulator.cli, "main")


class TestMaterializerKafkaConsumer:
    """Test materializer Kafka consumer."""

    def test_materializer_consumer_initialization(self):
        """Test materializer consumer initialization."""
        from services.materializer.kafka_consumer import MaterializerKafkaConsumer

        config = KafkaConfig()
        consumer = MaterializerKafkaConsumer(config)

        assert consumer.config == config
        assert consumer.consumer is not None  # Should be initialized
        assert not consumer.running

    @pytest.mark.asyncio
    async def test_materializer_consumer_connection_check(self):
        """Test materializer consumer connection check."""
        from services.materializer.kafka_consumer import MaterializerKafkaConsumer

        config = KafkaConfig()
        consumer = MaterializerKafkaConsumer(config)

        # Test connection check (should return False for mock/test environment)
        is_connected = await consumer.is_connected()
        # In test environment, this will likely be False since no real Kafka is running
        assert isinstance(is_connected, bool)

    @pytest.mark.asyncio
    async def test_materializer_consumer_close(self):
        """Test materializer consumer close."""
        from services.materializer.kafka_consumer import MaterializerKafkaConsumer

        config = KafkaConfig()
        consumer = MaterializerKafkaConsumer(config)

        # Should not raise exception
        await consumer.close()
        assert not consumer.running


class TestEdgeCasesAndErrorHandling:
    """Test edge cases and error handling."""

    @pytest.mark.asyncio
    async def test_run_simulation_for_profile_edge_cases(self):
        """Test run_simulation_for_profile with edge cases."""
        mock_producer = MockKafkaEventProducer(KafkaConfig())
        original_producer = services.simulator.main.producer
        services.simulator.main.producer = mock_producer

        try:
            # Test with 0 days
            await run_simulation_for_profile("profile-zero", 0, None)
            events = mock_producer.get_published_events()
            simulation_events = [
                e for e in events if e["event_type"] == "SimulationProgress"
            ]
            assert len(simulation_events) == 0

            # Clear events
            mock_producer.clear_published_events()

            # Test with negative days (should handle gracefully)
            await run_simulation_for_profile("profile-negative", -1, None)
            events = mock_producer.get_published_events()
            simulation_events = [
                e for e in events if e["event_type"] == "SimulationProgress"
            ]
            assert len(simulation_events) == 0

        finally:
            services.simulator.main.producer = original_producer

    @pytest.mark.asyncio
    async def test_process_event_with_different_event_types(self):
        """Test process_event with different event types."""
        mock_producer = MockKafkaEventProducer(KafkaConfig())
        original_producer = services.simulator.main.producer
        services.simulator.main.producer = mock_producer

        try:
            # Test with SimulationProgress event (should not trigger new simulation)
            sim_event = SimulationProgress(
                event_id="test-sim",
                timestamp=datetime.now(UTC),
                event_type="SimulationProgress",
                profile_id="profile-sim",
                day=1,
                ice_volume=Decimal("100.00"),
                manpower_hours=Decimal("50.00"),
                material_cost=Decimal("250.00"),
                labor_cost=Decimal("750.00"),
                total_cost=Decimal("1000.00"),
                cumulative_cost=Decimal("1000.00"),
            )

            await process_event(sim_event)

            # Should not generate additional simulation events
            events = mock_producer.get_published_events()
            new_simulation_events = [
                e for e in events if e["event_type"] == "SimulationProgress"
            ]
            assert len(new_simulation_events) == 0

        finally:
            services.simulator.main.producer = original_producer
