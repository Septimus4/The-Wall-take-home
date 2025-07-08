"""Tests for Kafka consumer functionality."""

from unittest.mock import Mock, patch

import pytest

from services.simulator.config import KafkaConfig
from services.simulator.kafka_consumer import KafkaEventConsumer


class TestKafkaEventConsumer:
    """Test cases for KafkaEventConsumer."""

    @pytest.fixture
    def kafka_config(self):
        """Create a test Kafka configuration."""
        return KafkaConfig(
            bootstrap_servers="localhost:9092",
            consumer_group="test-group",
            profile_topic="test-profiles",
            simulation_topic="test-simulation",
        )

    @pytest.fixture
    def consumer(self, kafka_config):
        """Create a KafkaEventConsumer instance."""
        return KafkaEventConsumer(kafka_config)

    def test_consumer_initialization(self, consumer, kafka_config):
        """Test consumer initialization."""
        assert consumer.config == kafka_config
        assert consumer.consumer is None
        assert not consumer._running

    @pytest.mark.asyncio
    @patch("services.simulator.kafka_consumer.Consumer")
    async def test_start_success(self, mock_consumer_class, consumer):
        """Test successful consumer start."""
        mock_consumer_instance = Mock()
        mock_consumer_class.return_value = mock_consumer_instance

        await consumer.start()

        # Verify consumer was created with correct config
        mock_consumer_class.assert_called_once()
        call_args = mock_consumer_class.call_args[0][0]
        assert call_args["bootstrap.servers"] == "localhost:9092"
        assert call_args["group.id"] == "test-group"

        # Verify subscribe was called
        mock_consumer_instance.subscribe.assert_called_once_with(["test-profiles"])
        assert consumer._running

    @pytest.mark.asyncio
    @patch("services.simulator.kafka_consumer.Consumer")
    async def test_start_failure(self, mock_consumer_class, consumer):
        """Test consumer start failure."""
        mock_consumer_class.side_effect = Exception("Connection failed")

        with pytest.raises(Exception, match="Connection failed"):
            await consumer.start()

    @pytest.mark.asyncio
    async def test_is_connected_false_no_consumer(self, consumer):
        """Test is_connected returns False when no consumer."""
        result = await consumer.is_connected()
        assert result is False
