"""Kafka event consumer for the simulation service."""

import asyncio
import json
from collections.abc import AsyncGenerator
from typing import Any

import structlog
from confluent_kafka import Consumer, KafkaError, KafkaException

from .config import KafkaConfig

logger = structlog.get_logger(__name__)


class KafkaEventConsumer:
    """Async Kafka event consumer."""

    def __init__(self, config: KafkaConfig):
        self.config = config
        self.consumer: Consumer | None = None
        self._running = False

    async def start(self) -> None:
        """Initialize and start the Kafka consumer."""
        consumer_config = {
            "bootstrap.servers": self.config.bootstrap_servers,
            "group.id": self.config.consumer_group,
            "auto.offset.reset": self.config.auto_offset_reset,
            "enable.auto.commit": self.config.enable_auto_commit,
            "auto.commit.interval.ms": self.config.auto_commit_interval_ms,
            # Add timeout settings to fail faster when Kafka is not available
            "socket.timeout.ms": 5000,
            "api.version.request.timeout.ms": 5000,
        }

        try:
            self.consumer = Consumer(consumer_config)
            self.consumer.subscribe([self.config.profile_topic])
            self._running = True

            logger.info(
                "Kafka consumer started",
                topics=[self.config.profile_topic],
                group_id=self.config.consumer_group,
            )

        except Exception as e:
            logger.error("Failed to start Kafka consumer", error=str(e))
            raise

    async def consume_events(self) -> AsyncGenerator[dict[str, Any], None]:
        """Consume events from Kafka topics."""
        if not self.consumer:
            await self.start()

        if not self.consumer:
            raise RuntimeError("Consumer not initialized")

        logger.info("Starting event consumption loop")

        try:
            while self._running:
                msg = await self._poll_message()
                if msg is None:
                    continue

                event_data = self._process_message(msg)
                if event_data is not None:
                    yield event_data

        except KafkaException as e:
            logger.error("Kafka exception in consumption loop", error=str(e))
            raise
        except Exception as e:
            logger.error("Unexpected error in consumption loop", error=str(e))
            raise

    async def _poll_message(self) -> Any:
        """Poll for a single message from Kafka."""
        msg = await asyncio.get_event_loop().run_in_executor(
            None, lambda: self.consumer.poll(timeout=1.0)  # type: ignore[union-attr]
        )

        if msg is None:
            # No message available, continue polling
            await asyncio.sleep(0.1)
            return None

        if msg.error():
            self._handle_message_error(msg)
            return None

        return msg

    def _handle_message_error(self, msg: Any) -> None:
        """Handle message errors."""
        if msg.error().code() == KafkaError._PARTITION_EOF:
            # End of partition, continue
            logger.debug(
                "Reached end of partition",
                partition=msg.partition(),
                offset=msg.offset(),
            )
        elif msg.error().code() == KafkaError.UNKNOWN_TOPIC_OR_PART:
            # Topic doesn't exist yet, this is normal during startup
            logger.debug("Topic not available yet", error=msg.error())
        else:
            logger.error("Kafka error", error=msg.error())

    def _process_message(self, msg: Any) -> dict[str, Any] | None:
        """Process a message and return event data."""
        try:
            # Decode message
            event_data = json.loads(msg.value().decode("utf-8"))

            logger.debug(
                "Received event",
                topic=msg.topic(),
                partition=msg.partition(),
                offset=msg.offset(),
                event_type=event_data.get("event_type"),
            )

            return event_data  # type: ignore[no-any-return]

        except json.JSONDecodeError as e:
            logger.error(
                "Failed to decode message JSON",
                message=msg.value(),
                error=str(e),
            )
            return None

        except Exception as e:
            logger.error("Unexpected error processing message", error=str(e))
            return None

    async def is_connected(self) -> bool:
        """Check if consumer is connected to Kafka."""
        if not self.consumer:
            return False

        try:
            # Try to get metadata (non-blocking check)
            metadata = await asyncio.get_event_loop().run_in_executor(
                None, lambda: self.consumer.list_topics(timeout=1.0)  # type: ignore[union-attr]
            )
            return metadata is not None
        except Exception:
            return False

    async def close(self) -> None:
        """Close the Kafka consumer."""
        self._running = False

        if self.consumer:
            try:
                await asyncio.get_event_loop().run_in_executor(
                    None, self.consumer.close
                )
                logger.info("Kafka consumer closed")
            except Exception as e:
                logger.error("Error closing Kafka consumer", error=str(e))
            finally:
                self.consumer = None
