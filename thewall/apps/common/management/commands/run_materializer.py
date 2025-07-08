"""
Django management command to run the materializer Kafka consumer.

This command consumes events from Kafka and updates read models in the database.
"""

import asyncio
import signal
import sys
from typing import Any

import structlog
from django.core.management.base import BaseCommand
from django.db import transaction

from apps.common.db_utils import ConnectionMonitorMixin, ensure_connection_cleanup
from apps.profiles.models import WallProfile
from services.materializer.kafka_consumer import MaterializerKafkaConsumer
from services.simulator.config import KafkaConfig
from shared.wall_common.events import (
    ProfileCreated,
    ProfileUpdated,
    SimulationProgress,
    deserialize_event,
)

logger = structlog.get_logger(__name__)


class Command(BaseCommand, ConnectionMonitorMixin):
    """Django management command to run the Kafka event consumer."""

    help_text = "Run the Kafka event consumer to materialize read models"

    def __init__(self, *args: Any, **kwargs: Any) -> None:
        super().__init__(*args, **kwargs)
        self.consumer: MaterializerKafkaConsumer | None = None
        self.running = True

    def add_arguments(self, parser: Any) -> None:
        """Add command line arguments."""
        parser.add_argument(
            "--kafka-servers",
            type=str,
            default="localhost:9092",
            help="Kafka bootstrap servers (default: localhost:9092)",
        )
        parser.add_argument(
            "--consumer-group",
            type=str,
            default="materializer",
            help="Kafka consumer group (default: materializer)",
        )
        parser.add_argument(
            "--topics",
            type=str,
            nargs="+",
            default=["wall.profiles", "wall.simulation"],
            help="Kafka topics to consume (default: wall.profiles wall.simulation)",
        )

    def handle(self, *_args: Any, **options: Any) -> None:
        """Handle the command execution."""
        # Configure structured logging
        structlog.configure(
            processors=[
                structlog.stdlib.filter_by_level,
                structlog.stdlib.add_logger_name,
                structlog.stdlib.add_log_level,
                structlog.stdlib.PositionalArgumentsFormatter(),
                structlog.dev.ConsoleRenderer(),
            ],
            wrapper_class=structlog.stdlib.BoundLogger,
            logger_factory=structlog.stdlib.LoggerFactory(),
            cache_logger_on_first_use=True,
        )

        # Set up signal handlers for graceful shutdown
        signal.signal(signal.SIGINT, self._signal_handler)
        signal.signal(signal.SIGTERM, self._signal_handler)

        try:
            # Run the async consumer
            asyncio.run(self._run_consumer(options))
        except KeyboardInterrupt:
            self.stdout.write("Received interrupt signal, shutting down...")
        except Exception as e:
            logger.error("Materializer failed", error=str(e))
            sys.exit(1)

    def _signal_handler(self, signum: int, _frame: Any) -> None:
        """Handle shutdown signals."""
        logger.info("Received shutdown signal", signal=signum)
        self.running = False

    async def _run_consumer(self, options: dict[str, Any]) -> None:
        """Run the Kafka consumer loop."""
        # Log initial connection info
        self.log_connection_health()

        # Create Kafka configuration
        kafka_config = KafkaConfig(
            bootstrap_servers=options["kafka_servers"],
            profile_topic=options["topics"][0]
            if len(options["topics"]) > 0
            else "wall.profiles",
            simulation_topic=options["topics"][1]
            if len(options["topics"]) > 1
            else "wall.simulation",
            consumer_group=options["consumer_group"],
        )

        # Initialize consumer
        self.consumer = MaterializerKafkaConsumer(kafka_config)

        try:
            await self.consumer.start()
            logger.info(
                "Materializer started",
                bootstrap_servers=kafka_config.bootstrap_servers,
                consumer_group=kafka_config.consumer_group,
                topics=options["topics"],
            )

            # Main consumer loop with connection monitoring
            async for event_data in self.consumer.consume_events():
                if not self.running:
                    break

                try:
                    await self._process_event(event_data)
                except Exception as e:
                    logger.error(
                        "Failed to process event", event_data=event_data, error=str(e)
                    )
                    # Log connection status on errors
                    try:
                        from apps.common.db_utils import check_connection_health

                        health = check_connection_health()
                        if (
                            health["postgresql_info"]
                            and health["postgresql_info"]["utilization_percent"] > 85
                        ):
                            logger.warning(
                                "High database connection utilization detected",
                                utilization=health["postgresql_info"][
                                    "utilization_percent"
                                ],
                            )
                    except Exception:
                        pass  # Don't fail on monitoring errors

                    # Continue processing other events

        except Exception as e:
            logger.error("Consumer failed", error=str(e))
            # Log final connection status
            self.log_connection_health()
            raise
        finally:
            if self.consumer:
                await self.consumer.close()
                logger.info("Materializer stopped")
                # Ensure connection cleanup
                ensure_connection_cleanup()

    async def _process_event(self, event_data: dict[str, Any]) -> None:
        """Process a single event and update read models."""
        try:
            # Deserialize the event
            event = deserialize_event(event_data)

            logger.info(
                "Processing event", event_type=event.event_type, event_id=event.event_id
            )

            # Handle different event types
            if isinstance(event, ProfileCreated):
                await self._handle_profile_created(event)
            elif isinstance(event, ProfileUpdated):
                await self._handle_profile_updated(event)
            elif isinstance(event, SimulationProgress):
                await self._handle_simulation_progress(event)
            else:
                logger.debug("Ignoring event type", event_type=event.event_type)

        except Exception as e:
            logger.error("Failed to process event", event_data=event_data, error=str(e))
            raise

    async def _handle_profile_created(self, event: ProfileCreated) -> None:
        """Handle ProfileCreated event by creating/updating the read model."""
        try:
            with transaction.atomic():
                profile, created = WallProfile.objects.update_or_create(
                    profile_id=event.profile_id,
                    defaults={
                        "name": event.name,
                        "height": event.height,
                        "length": event.length,
                        "width": event.width,
                        "ice_thickness": event.ice_thickness,
                        "created_by": event.created_by,
                        "created_at": event.timestamp,
                        "updated_at": event.timestamp,
                    },
                )

                action = "created" if created else "updated"
                logger.info(
                    f"Profile {action}", profile_id=event.profile_id, name=event.name
                )

        except Exception as e:
            logger.error(
                "Failed to handle ProfileCreated event",
                profile_id=event.profile_id,
                error=str(e),
            )
            raise

    async def _handle_profile_updated(self, event: ProfileUpdated) -> None:
        """Handle ProfileUpdated event by updating the read model."""
        try:
            with transaction.atomic():
                try:
                    profile = WallProfile.objects.get(profile_id=event.profile_id)

                    # Update only the fields that are provided
                    updated_fields = []
                    if event.name is not None:
                        profile.name = event.name
                        updated_fields.append("name")
                    if event.height is not None:
                        profile.height = event.height
                        updated_fields.append("height")
                    if event.length is not None:
                        profile.length = event.length
                        updated_fields.append("length")
                    if event.width is not None:
                        profile.width = event.width
                        updated_fields.append("width")
                    if event.ice_thickness is not None:
                        profile.ice_thickness = event.ice_thickness
                        updated_fields.append("ice_thickness")
                    if event.updated_by is not None:
                        profile.updated_by = event.updated_by
                        updated_fields.append("updated_by")

                    profile.updated_at = event.timestamp
                    updated_fields.append("updated_at")

                    profile.save(update_fields=updated_fields)

                    logger.info(
                        "Profile updated",
                        profile_id=event.profile_id,
                        updated_fields=updated_fields,
                    )

                except WallProfile.DoesNotExist:
                    logger.warning(
                        "Profile not found for update", profile_id=event.profile_id
                    )

        except Exception as e:
            logger.error(
                "Failed to handle ProfileUpdated event",
                profile_id=event.profile_id,
                error=str(e),
            )
            raise

    async def _handle_simulation_progress(self, event: SimulationProgress) -> None:
        """Handle SimulationProgress event by updating simulation stats."""
        try:
            with transaction.atomic():
                try:
                    profile = WallProfile.objects.get(profile_id=event.profile_id)

                    # Update simulation progress fields
                    profile.last_simulation_day = event.day
                    profile.last_simulation_cost = event.cumulative_cost
                    profile.last_simulation_at = event.timestamp

                    profile.save(
                        update_fields=[
                            "last_simulation_day",
                            "last_simulation_cost",
                            "last_simulation_at",
                        ]
                    )

                    logger.debug(
                        "Simulation progress updated",
                        profile_id=event.profile_id,
                        day=event.day,
                        cumulative_cost=float(event.cumulative_cost),
                    )

                except WallProfile.DoesNotExist:
                    logger.warning(
                        "Profile not found for simulation progress",
                        profile_id=event.profile_id,
                    )

        except Exception as e:
            logger.error(
                "Failed to handle SimulationProgress event",
                profile_id=event.profile_id,
                day=event.day,
                error=str(e),
            )
            raise
