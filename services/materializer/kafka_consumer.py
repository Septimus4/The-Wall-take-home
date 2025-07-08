"""Kafka consumer implementation for materializer."""

import asyncio
import json
from collections.abc import AsyncGenerator
from typing import Any

import structlog
from confluent_kafka import Consumer, KafkaError, KafkaException

from services.simulator.config import KafkaConfig

logger = structlog.get_logger(__name__)


class MaterializerKafkaConsumer:
    """Kafka consumer for materializer service."""

    def __init__(self, config: KafkaConfig):
        self.config = config
        self.consumer: Consumer | None = None
        self.running = False
        self._initialize_consumer()

    def _initialize_consumer(self) -> None:
        """Initialize the Kafka consumer."""
        consumer_config = {
            "bootstrap.servers": self.config.bootstrap_servers,
            "group.id": self.config.consumer_group,
            "auto.offset.reset": "earliest",
            "enable.auto.commit": True,
            "auto.commit.interval.ms": 5000,
        }

        try:
            self.consumer = Consumer(consumer_config)
            logger.info(
                "Materializer Kafka consumer initialized",
                bootstrap_servers=self.config.bootstrap_servers,
                consumer_group=self.config.consumer_group,
            )
        except Exception as e:
            logger.error("Failed to initialize Kafka consumer", error=str(e))
            raise

    async def start(self) -> None:
        """Start the consumer and subscribe to topics."""
        if not self.consumer:
            raise RuntimeError("Consumer not initialized")

        topics = [self.config.profile_topic, self.config.simulation_topic]

        try:
            self.consumer.subscribe(topics)
            self.running = True
            logger.info("Materializer consumer started", topics=topics)
        except Exception as e:
            logger.error("Failed to start consumer", error=str(e))
            raise

    async def consume_events(self) -> AsyncGenerator[dict[str, Any], None]:
        """Consume events from Kafka topics."""
        if not self.consumer or not self.running:
            raise RuntimeError("Consumer not started")

        logger.info("Starting event consumption loop")

        while self.running:
            try:
                if not self.consumer:
                    raise RuntimeError("Consumer not initialized")

                # Poll for messages with timeout
                msg = await asyncio.get_event_loop().run_in_executor(
                    None, lambda: self.consumer.poll(timeout=1.0)  # type: ignore[union-attr]
                )

                if msg is None:
                    # No message received, continue polling
                    continue

                if msg.error():
                    if msg.error().code() == KafkaError._PARTITION_EOF:
                        # End of partition, continue
                        continue
                    else:
                        logger.error("Kafka error", error=str(msg.error()))
                        raise KafkaException(msg.error())

                # Parse the message
                try:
                    event_data = json.loads(msg.value().decode("utf-8"))

                    logger.debug(
                        "Received event",
                        topic=msg.topic(),
                        partition=msg.partition(),
                        offset=msg.offset(),
                        event_type=event_data.get("event_type"),
                    )

                    yield event_data

                except json.JSONDecodeError as e:
                    logger.error(
                        "Failed to decode JSON message",
                        topic=msg.topic(),
                        offset=msg.offset(),
                        error=str(e),
                    )
                    continue

            except asyncio.CancelledError:
                logger.info("Consumer cancelled")
                break
            except Exception as e:
                logger.error("Error in consumer loop", error=str(e))
                # Don't break the loop for individual message errors
                await asyncio.sleep(1)

    async def is_connected(self) -> bool:
        """Check if consumer is connected to Kafka."""
        if not self.consumer:
            return False

        try:
            # Try to get metadata (non-blocking check)
            metadata = await asyncio.get_event_loop().run_in_executor(
                None,
                lambda: self.consumer.list_topics(timeout=1.0)
                if self.consumer
                else None,
            )
            return metadata is not None
        except Exception:
            return False

    async def close(self) -> None:
        """Close the Kafka consumer."""
        self.running = False

        if self.consumer:
            try:
                await asyncio.get_event_loop().run_in_executor(
                    None, self.consumer.close
                )
                logger.info("Materializer Kafka consumer closed")
            except Exception as e:
                logger.error("Error closing Kafka consumer", error=str(e))
            finally:
                self.consumer = None
