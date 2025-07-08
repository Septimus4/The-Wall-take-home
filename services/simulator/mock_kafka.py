"""Mock Kafka implementation for local development and testing."""

import asyncio
from collections.abc import AsyncGenerator
from typing import Any

import structlog

from shared.wall_common.events import BaseEvent

from .config import KafkaConfig

logger = structlog.get_logger(__name__)


class MockKafkaEventConsumer:
    """Mock Kafka consumer for local development."""

    def __init__(self, config: KafkaConfig):
        self.config = config
        self._running = False
        self._message_queue: asyncio.Queue[dict[str, Any]] = asyncio.Queue()

    async def start(self) -> None:
        """Start the mock consumer."""
        self._running = True
        logger.info("Mock Kafka consumer started (no real Kafka connection)")

    async def consume_events(self) -> AsyncGenerator[dict[str, Any], None]:
        """Mock event consumption - yields queued events."""
        if not self._running:
            await self.start()

        logger.info("Starting mock event consumption loop")

        while self._running:
            try:
                # Wait for events in the queue with timeout
                event_data = await asyncio.wait_for(
                    self._message_queue.get(), timeout=1.0
                )

                logger.debug(
                    "Mock consumer received event",
                    event_type=event_data.get("event_type"),
                )
                yield event_data

            except asyncio.TimeoutError:
                # No messages, continue
                await asyncio.sleep(0.1)
                continue

    async def add_mock_event(self, event_data: dict[str, Any]) -> None:
        """Add a mock event to the queue for testing."""
        await self._message_queue.put(event_data)
        logger.debug(
            "Added mock event to queue", event_type=event_data.get("event_type")
        )

    async def is_connected(self) -> bool:
        """Mock connection check - always returns True."""
        return True

    async def close(self) -> None:
        """Close the mock consumer."""
        self._running = False
        logger.info("Mock Kafka consumer closed")


class MockKafkaEventProducer:
    """Mock Kafka producer for local development."""

    def __init__(self, config: KafkaConfig):
        self.config = config
        self._published_events: list[dict[str, Any]] = []

    async def publish_event(self, event: BaseEvent) -> None:
        """Mock event publishing - just logs the event."""
        event_data = event.to_dict()
        self._published_events.append(event_data)

        topic = self._get_topic_for_event_type(event.event_type)

        logger.info(
            "Mock event published",
            event_type=event.event_type,
            event_id=event.event_id,
            topic=topic,
            profile_id=event_data.get("profile_id"),
        )

    def _get_topic_for_event_type(self, event_type: str) -> str:
        """Get the topic for event type (same logic as real producer)."""
        topic_mapping = {
            "ProfileCreated": self.config.profile_topic,
            "ProfileUpdated": self.config.profile_topic,
            "SimulationProgress": self.config.simulation_topic,
        }
        return topic_mapping.get(event_type, self.config.simulation_topic)

    async def flush(self) -> None:
        """Mock flush - no-op."""
        logger.debug("Mock producer flushed")

    async def is_connected(self) -> bool:
        """Mock connection check - always returns True."""
        return True

    async def close(self) -> None:
        """Close the mock producer."""
        logger.info(
            "Mock Kafka producer closed",
            total_events_published=len(self._published_events),
        )

    def get_published_events(self) -> list[dict[str, Any]]:
        """Get all published events for testing."""
        return self._published_events.copy()

    def clear_published_events(self) -> None:
        """Clear published events for testing."""
        self._published_events.clear()
