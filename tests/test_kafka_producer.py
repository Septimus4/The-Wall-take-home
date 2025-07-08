"""Tests for Kafka producer functionality."""

from unittest.mock import Mock, patch

import pytest

from services.simulator.config import KafkaConfig
from services.simulator.kafka_producer import KafkaEventProducer


class TestKafkaEventProducer:
    """Test cases for KafkaEventProducer."""

    @pytest.fixture
    def kafka_config(self):
        """Create a test Kafka configuration."""
        return KafkaConfig(
            bootstrap_servers="localhost:9092",
            profile_topic="test-profiles",
            simulation_topic="test-simulation",
        )

    @pytest.fixture
    def producer(self, kafka_config):
        """Create a KafkaEventProducer instance."""
        with patch("services.simulator.kafka_producer.Producer"):
            return KafkaEventProducer(kafka_config)

    def test_producer_initialization(self, kafka_config):
        """Test producer initialization."""
        with patch("services.simulator.kafka_producer.Producer") as mock_producer_class:
            mock_producer_instance = Mock()
            mock_producer_class.return_value = mock_producer_instance

            producer = KafkaEventProducer(kafka_config)

            # Verify producer was created with correct config
            mock_producer_class.assert_called_once()
            call_args = mock_producer_class.call_args[0][0]
            assert call_args["bootstrap.servers"] == "localhost:9092"
            assert "acks" in call_args
            assert "retries" in call_args

            assert producer.config == kafka_config
            assert producer.producer == mock_producer_instance

    def test_producer_initialization_failure(self, kafka_config):
        """Test producer initialization failure."""
        with patch(
            "services.simulator.kafka_producer.Producer",
            side_effect=Exception("Init failed"),
        ), pytest.raises(Exception, match="Init failed"):
            KafkaEventProducer(kafka_config)

    def test_delivery_callback_success(self, producer):
        """Test delivery callback with successful delivery."""
        mock_msg = Mock()
        mock_msg.topic.return_value = "test-topic"
        mock_msg.partition.return_value = 0
        mock_msg.offset.return_value = 123

        # Should not raise exception
        producer._delivery_callback(None, mock_msg)

    def test_delivery_callback_error(self, producer):
        """Test delivery callback with delivery error."""
        mock_error = Mock()
        mock_error.__str__ = Mock(return_value="Delivery failed")  # type: ignore[method-assign]
        mock_msg = Mock()
        mock_msg.topic.return_value = "test-topic"
        mock_msg.partition.return_value = 0

        # Should not raise exception but log error
        producer._delivery_callback(mock_error, mock_msg)

    def test_get_topic_for_event_type_profile_created(self, producer):
        """Test topic mapping for ProfileCreated event."""
        topic = producer._get_topic_for_event_type("ProfileCreated")
        assert topic == "test-profiles"

    def test_get_topic_for_event_type_profile_updated(self, producer):
        """Test topic mapping for ProfileUpdated event."""
        topic = producer._get_topic_for_event_type("ProfileUpdated")
        assert topic == "test-profiles"

    def test_get_topic_for_event_type_simulation_progress(self, producer):
        """Test topic mapping for SimulationProgress event."""
        topic = producer._get_topic_for_event_type("SimulationProgress")
        assert topic == "test-simulation"

    def test_get_topic_for_event_type_unknown(self, producer):
        """Test topic mapping for unknown event type."""
        topic = producer._get_topic_for_event_type("UnknownEvent")
        assert topic == "test-simulation"  # Default topic
