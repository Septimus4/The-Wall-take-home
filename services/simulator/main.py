"""FastAPI simulation service for wall construction simulation."""

import asyncio
import contextlib
from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager
from datetime import UTC, datetime
from decimal import Decimal
from typing import Any

import structlog
from fastapi import BackgroundTasks, FastAPI
from pydantic import BaseModel

from shared.wall_common.calcs import WallProfile, simulate_daily_progress
from shared.wall_common.events import (
    ProfileCreated,
    SimulationProgress,
    deserialize_event,
)

from .config import SimulatorConfig
from .kafka_consumer import KafkaEventConsumer
from .kafka_producer import KafkaEventProducer
from .mock_kafka import MockKafkaEventConsumer, MockKafkaEventProducer

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

logger = structlog.get_logger(__name__)


class HealthResponse(BaseModel):
    """Health check response model."""

    status: str
    version: str
    kafka_connected: bool


class SimulationRequest(BaseModel):
    """Manual simulation request model."""

    profile_id: str
    days: int = 1


# Global state
consumer: KafkaEventConsumer | None = None
producer: KafkaEventProducer | None = None
config = SimulatorConfig()


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """Application lifespan manager."""
    global consumer, producer

    logger.info("Starting simulation service", version=config.version)

    try:
        # Initialize Kafka components (try real Kafka first, fallback to mock)
        try:
            producer = KafkaEventProducer(config.kafka_config)
            consumer = KafkaEventConsumer(config.kafka_config)
            await consumer.start()
            logger.info("Using real Kafka implementation")
        except Exception as kafka_error:
            logger.warning(
                "Failed to connect to Kafka, using mock implementation",
                error=str(kafka_error),
            )
            producer = MockKafkaEventProducer(config.kafka_config)  # type: ignore[assignment]
            consumer = MockKafkaEventConsumer(config.kafka_config)  # type: ignore[assignment]
            await consumer.start()  # type: ignore[union-attr]

        # Start background consumer task
        consumer_task = asyncio.create_task(run_event_consumer())

        logger.info("Simulation service started successfully")
        yield

    except Exception as e:
        logger.error("Failed to start simulation service", error=str(e))
        raise
    finally:
        logger.info("Shutting down simulation service")

        # Cancel consumer task
        if "consumer_task" in locals():
            consumer_task.cancel()
            with contextlib.suppress(asyncio.CancelledError):
                await consumer_task

        # Close Kafka connections
        if consumer:
            await consumer.close()
        if producer:
            await producer.close()


app = FastAPI(
    title="Wall Simulation Service",
    description="Event-driven wall construction simulation service",
    version=config.version,
    lifespan=lifespan,
)


@app.get("/health", response_model=HealthResponse)
async def health_check() -> HealthResponse:
    """Health check endpoint."""
    kafka_connected = (
        producer is not None
        and consumer is not None
        and await producer.is_connected()
        and await consumer.is_connected()
    )

    return HealthResponse(
        status="healthy" if kafka_connected else "degraded",
        version=config.version,
        kafka_connected=kafka_connected,
    )


@app.get("/metrics")
async def metrics() -> dict[str, Any]:
    """Prometheus metrics endpoint."""
    kafka_connected = (
        producer is not None
        and consumer is not None
        and await producer.is_connected()
        and await consumer.is_connected()
    )

    return {
        "simulator_up": 1,
        "simulator_kafka_connected": 1 if kafka_connected else 0,
        "simulator_version_info": {"version": config.version},
    }


@app.post("/simulate")
async def trigger_simulation(
    request: SimulationRequest, background_tasks: BackgroundTasks
) -> dict[str, Any]:
    """Manually trigger simulation for a profile."""
    if not producer:
        return {"error": "Producer not initialized"}

    background_tasks.add_task(
        run_simulation_for_profile, request.profile_id, request.days
    )

    return {
        "message": f"Simulation triggered for profile {request.profile_id}",
        "days": request.days,
    }


@app.post("/test/inject-profile-created")
async def inject_mock_profile_created(profile_data: dict[str, Any]) -> dict[str, Any]:
    """Inject a mock ProfileCreated event for testing (only works with mock consumer)."""
    from .mock_kafka import MockKafkaEventConsumer

    if not isinstance(consumer, MockKafkaEventConsumer):
        return {"error": "This endpoint only works with mock Kafka implementation"}

    # Create a ProfileCreated event from the provided data
    from datetime import datetime
    from decimal import Decimal

    from shared.wall_common.events import ProfileCreated

    try:
        profile_event = ProfileCreated(
            event_id="",
            timestamp=datetime.now(UTC),
            event_type="ProfileCreated",
            profile_id=profile_data["profile_id"],
            name=profile_data["name"],
            height=Decimal(str(profile_data["height"])),
            length=Decimal(str(profile_data["length"])),
            width=Decimal(str(profile_data["width"])),
            ice_thickness=Decimal(str(profile_data["ice_thickness"])),
            created_by=profile_data.get("created_by"),
        )

        # Inject the event into the mock consumer
        await consumer.add_mock_event(profile_event.to_dict())

        return {
            "message": "ProfileCreated event injected successfully",
            "profile_id": profile_data["profile_id"],
        }

    except Exception as e:
        return {"error": f"Failed to inject event: {str(e)}"}


async def run_event_consumer() -> None:
    """Background task to consume and process events."""
    if not consumer:
        logger.error("Consumer not initialized")
        return

    logger.info("Starting event consumer loop")

    try:
        async for event_data in consumer.consume_events():
            try:
                event = deserialize_event(event_data)
                await process_event(event)
            except Exception as e:
                logger.error(
                    "Failed to process event", event_data=event_data, error=str(e)
                )
                # Continue processing other events

    except Exception as e:
        logger.error("Event consumer loop failed", error=str(e))
        raise


async def process_event(event: Any) -> None:
    """Process incoming events based on type."""
    logger.info(
        "Processing event", event_type=event.event_type, event_id=event.event_id
    )

    if isinstance(event, ProfileCreated):
        await handle_profile_created(event)
    else:
        logger.debug("Ignoring event type", event_type=event.event_type)


async def handle_profile_created(event: ProfileCreated) -> None:
    """Handle ProfileCreated event by starting simulation."""
    logger.info(
        "Starting simulation for new profile",
        profile_id=event.profile_id,
        name=event.name,
    )

    # Start simulation for the first few days
    initial_days = config.initial_simulation_days
    await run_simulation_for_profile(event.profile_id, initial_days, event)


async def run_simulation_for_profile(
    profile_id: str, days: int, profile_event: ProfileCreated | None = None
) -> None:
    """Run simulation for a specific profile."""
    if not producer:
        logger.error("Producer not available for simulation")
        return

    try:
        # If we don't have the profile event, we'd need to fetch it from a store
        # For now, assume we have it from the event
        if not profile_event:
            logger.warning(
                "Profile data not available, skipping simulation", profile_id=profile_id
            )
            return

        # Convert event to WallProfile for calculations
        wall_profile = WallProfile(
            name=profile_event.name,
            height=profile_event.height,
            length=profile_event.length,
            width=profile_event.width,
            ice_thickness=profile_event.ice_thickness,
        )

        logger.info(
            "Running simulation",
            profile_id=profile_id,
            days=days,
            profile=wall_profile.name,
        )

        cumulative_cost = Decimal("0")

        for day in range(1, days + 1):
            # Calculate daily progress
            daily_stats = simulate_daily_progress(wall_profile, day, cumulative_cost)
            cumulative_cost = daily_stats.cumulative_cost

            # Create simulation progress event
            progress_event = SimulationProgress(
                event_id="",  # Will be auto-generated
                timestamp=datetime.now(),  # Will be auto-generated
                event_type="",  # Will be set in __post_init__
                profile_id=profile_id,
                day=daily_stats.day,
                ice_volume=daily_stats.ice_volume,
                manpower_hours=daily_stats.manpower_hours,
                material_cost=daily_stats.material_cost,
                labor_cost=daily_stats.labor_cost,
                total_cost=daily_stats.total_cost,
                cumulative_cost=daily_stats.cumulative_cost,
            )

            # Publish simulation progress event
            await producer.publish_event(progress_event)

            logger.debug(
                "Published simulation progress",
                profile_id=profile_id,
                day=day,
                cumulative_cost=float(cumulative_cost),
            )

        logger.info(
            "Simulation completed",
            profile_id=profile_id,
            days=days,
            final_cumulative_cost=float(cumulative_cost),
        )

    except Exception as e:
        logger.error("Simulation failed", profile_id=profile_id, error=str(e))
        raise


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "services.simulator.main:app",
        host="0.0.0.0",
        port=9000,
        reload=True,
        log_level="info",
    )
