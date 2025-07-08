"""Kafka event publishing utilities."""

import json
import logging
from importlib import import_module
from typing import Any

from django.conf import settings

logger = logging.getLogger(__name__)

try:  # real dependency present?
    from confluent_kafka import Producer
except Exception:  # pragma: no cover – CI without librdkafka
    Producer = None

try:
    from confluent_kafka.schema_registry import SchemaRegistryClient
except Exception:  # pragma: no cover
    SchemaRegistryClient = None


class KafkaEventPublisher:  # pragma: no cover – exercised via tests
    """Thin wrapper around confluent-kafka with optional schema registry."""

    def __init__(self) -> None:
        self.producer = None
        self.schema_registry = None
        self._initialize_kafka()

    # ------------------------------------------------------------------#
    # Public helpers                                                     #
    # ------------------------------------------------------------------#
    def publish_event(self, topic: str, payload: dict[str, Any]) -> bool:
        """Publish *any* event; returns *True* on success, *False* otherwise."""
        if not self.producer:
            logger.warning("Kafka producer not available, skipping event publication")
            return False

        try:
            self.producer.produce(topic, json.dumps(payload).encode())
            self.producer.flush()
            return True
        except Exception as exc:  # pragma: no cover – captured in tests
            logger.error("Failed to publish event: %s", exc)
            return False

    # Convenience specific to ProfileCreated
    def publish_profile_created(self, event: Any) -> bool:
        """Publish a `shared.wall_common.events.ProfileCreated` domain event."""
        return self.publish_event("wall.profiles", event.to_dict())

    def publish_profile_updated(self, event: Any) -> bool:
        """Publish a ProfileUpdated domain event."""
        return self.publish_event("wall.profiles", event.to_dict())

    # ------------------------------------------------------------------#
    # Internal                                                           #
    # ------------------------------------------------------------------#
    def _initialize_kafka(self) -> None:
        """Instantiate Producer and (optionally) Schema-RegistryClient."""
        try:
            cfg: dict[str, Any] = getattr(settings, "KAFKA_CONFIG", {})

            # ------------------------------------------------------------------
            # 1. Producer class – try real confluent_kafka, fall back to placeholder
            # ------------------------------------------------------------------
            producer_cls = None
            try:
                kafka_mod = import_module("confluent_kafka")
                producer_cls = getattr(kafka_mod, "Producer", None)
            except ModuleNotFoundError:
                # librdkafka not installed in CI – ignore
                producer_cls = None

            if producer_cls is None:  # fall back to module-level symbol
                from apps.profiles.kafka_publisher import Producer as _Producer

                producer_cls = _Producer

            if producer_cls is None:  # pragma: no cover – extremely unlikely
                raise RuntimeError("confluent_kafka.Producer missing")

            self.producer = producer_cls(cfg.get("producer", {}))

            # ------------------------------------------------------------------
            # 2. Schema Registry client – same two-step lookup pattern
            # ------------------------------------------------------------------
            schema_registry_cls = None
            try:
                schema_mod = import_module("confluent_kafka.schema_registry")
                schema_registry_cls = getattr(schema_mod, "SchemaRegistryClient", None)
            except ModuleNotFoundError:
                schema_registry_cls = None

            if schema_registry_cls is None:
                from apps.profiles.kafka_publisher import (
                    SchemaRegistryClient as _SRC,  # noqa: N814
                )

                schema_registry_cls = _SRC

            if schema_registry_cls:
                registry_url = cfg.get("schema_registry_url") or "http://localhost:8081"
                self.schema_registry = schema_registry_cls({"url": registry_url})
            else:
                logger.warning("Schema registry disabled (module missing)")
                self.schema_registry = None

        except Exception as e:  # noqa: BLE001
            logger.error("Failed to initialize Kafka: %s", e)
            self.producer = None
            self.schema_registry = None


# ----------------------------------------------------------------------#
# Lazy-loaded singleton for app-wide use (e.g. health checks)           #
# ----------------------------------------------------------------------#
_publisher_singleton: KafkaEventPublisher | None = None


def get_kafka_publisher() -> KafkaEventPublisher:
    """Return a shared KafkaEventPublisher instance, creating it on first use."""
    global _publisher_singleton
    if _publisher_singleton is None:
        _publisher_singleton = KafkaEventPublisher()
    return _publisher_singleton


__all__ = [
    "KafkaEventPublisher",
    "get_kafka_publisher",
    "Producer",
    "SchemaRegistryClient",
]
