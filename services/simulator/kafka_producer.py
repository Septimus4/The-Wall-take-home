"""Kafka event producer for the simulation service."""

import asyncio
import json
from typing import Any

import structlog
from confluent_kafka import KafkaError, Producer

from shared.wall_common.events import BaseEvent

from .config import KafkaConfig

logger = structlog.get_logger(__name__)


class KafkaEventProducer:
    """Async Kafka event producer."""

    def __init__(self, config: KafkaConfig):
        self.config = config
        self.producer: Producer | None = None
        self._initialize_producer()

    def _initialize_producer(self) -> None:
        """Initialize the Kafka producer."""
        producer_config = {
            "bootstrap.servers": self.config.bootstrap_servers,
            "acks": self.config.acks,
            "retries": self.config.retries,
            "batch.size": self.config.batch_size,
            "linger.ms": self.config.linger_ms,
        }

        try:
            self.producer = Producer(producer_config)
            logger.info(
                "Kafka producer initialized",
                bootstrap_servers=self.config.bootstrap_servers,
            )
        except Exception as e:
            logger.error("Failed to initialize Kafka producer", error=str(e))
            raise

    def _delivery_callback(self, err: KafkaError | None, msg: Any) -> None:
        """Callback for message delivery confirmation."""
        if err is not None:
            logger.error(
                "Message delivery failed",
                error=str(err),
                topic=msg.topic() if msg else None,
                partition=msg.partition() if msg else None,
            )
        else:
            logger.debug(
                "Message delivered successfully",
                topic=msg.topic(),
                partition=msg.partition(),
                offset=msg.offset(),
            )

    async def publish_event(self, event: BaseEvent) -> None:
        """Publish an event to the appropriate Kafka topic."""
        if not self.producer:
            raise RuntimeError("Producer not initialized")

        try:
            # Convert event to dictionary for JSON serialization
            event_data = event.to_dict()
            message_value = json.dumps(event_data, default=str)

            # Determine topic based on event type
            topic = self._get_topic_for_event_type(event.event_type)

            # Produce message asynchronously
            await asyncio.get_event_loop().run_in_executor(
                None,
                lambda: self.producer.produce(  # type: ignore[union-attr]
                    topic=topic,
                    value=message_value,
                    key=event_data.get("profile_id"),  # Use profile_id as partition key
                    callback=self._delivery_callback,
                ),
            )

            # Ensure message is sent
            await asyncio.get_event_loop().run_in_executor(
                None, lambda: self.producer.poll(0)  # type: ignore[union-attr]
            )

            logger.debug(
                "Event published",
                event_type=event.event_type,
                event_id=event.event_id,
                topic=topic,
            )

        except Exception as e:
            logger.error(
                "Failed to publish event",
                event_type=event.event_type,
                event_id=event.event_id,
                error=str(e),
            )
            raise

    def _get_topic_for_event_type(self, event_type: str) -> str:
        """Get the Kafka topic for a given event type."""
        topic_mapping = {
            "ProfileCreated": self.config.profile_topic,
            "ProfileUpdated": self.config.profile_topic,
            "SimulationProgress": self.config.simulation_topic,
        }

        return topic_mapping.get(event_type, self.config.simulation_topic)

    async def flush(self) -> None:
        """Flush any pending messages."""
        if self.producer:
            await asyncio.get_event_loop().run_in_executor(
                None, lambda: self.producer.flush(timeout=10.0)  # type: ignore[union-attr]
            )
            logger.debug("Producer flushed")

    async def is_connected(self) -> bool:
        """Check if producer is connected to Kafka."""
        if not self.producer:
            return False

        try:
            # Try to get metadata (non-blocking check)
            metadata = await asyncio.get_event_loop().run_in_executor(
                None, lambda: self.producer.list_topics(timeout=1.0)  # type: ignore[union-attr]
            )
            return metadata is not None
        except Exception:
            return False

    async def close(self) -> None:
        """Close the Kafka producer."""
        if self.producer:
            try:
                await self.flush()
                # Close producer gracefully (confluent-kafka uses close() method)
                self.producer.close()
                logger.info("Kafka producer closed")
            except Exception as e:
                logger.error("Error closing Kafka producer", error=str(e))
            finally:
                self.producer = None
