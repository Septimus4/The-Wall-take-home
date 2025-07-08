"""Tests for materializer Kafka consumer functionality."""

from unittest.mock import Mock, patch

import pytest

from services.materializer.kafka_consumer import MaterializerKafkaConsumer
from services.simulator.config import KafkaConfig


class TestMaterializerKafkaConsumer:
    """Test cases for MaterializerKafkaConsumer."""

    @pytest.fixture
    def kafka_config(self):
        """Create a test Kafka configuration."""
        return KafkaConfig(
            bootstrap_servers="localhost:9092",
            consumer_group="materializer-group",
            profile_topic="test-profiles",
            simulation_topic="test-simulation",
        )

    @pytest.fixture
    def consumer(self, kafka_config):
        """Create a MaterializerKafkaConsumer instance."""
        with patch("services.materializer.kafka_consumer.Consumer"):
            return MaterializerKafkaConsumer(kafka_config)

    def test_consumer_initialization(self, kafka_config):
        """Test consumer initialization."""
        with patch(
            "services.materializer.kafka_consumer.Consumer"
        ) as mock_consumer_class:
            mock_consumer_instance = Mock()
            mock_consumer_class.return_value = mock_consumer_instance

            consumer = MaterializerKafkaConsumer(kafka_config)

            # Verify consumer was created with correct config
            mock_consumer_class.assert_called_once()
            call_args = mock_consumer_class.call_args[0][0]
            assert call_args["bootstrap.servers"] == "localhost:9092"
            assert call_args["group.id"] == "materializer-group"
            assert call_args["auto.offset.reset"] == "earliest"

            assert consumer.config == kafka_config
            assert consumer.consumer == mock_consumer_instance
            assert not consumer.running

    def test_consumer_initialization_failure(self, kafka_config):
        """Test consumer initialization failure."""
        with patch(
            "services.materializer.kafka_consumer.Consumer",
            side_effect=Exception("Init failed"),
        ), pytest.raises(Exception, match="Init failed"):
            MaterializerKafkaConsumer(kafka_config)
