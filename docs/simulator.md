# Simulation Service Documentation

The Simulation Service is a high-performance FastAPI application that processes wall construction simulations using event-driven architecture.

## Overview

The simulator consumes `ProfileCreated` and `ProfileUpdated` events from Kafka, runs daily construction simulations, and publishes progress updates back to the event stream.

## Service Details

- **Technology**: FastAPI with async/await
- **Port**: `8001` (configurable)
- **Documentation**: http://localhost:8001/docs
- **Health Check**: http://localhost:8001/health

## Event Schemas

The simulator works with Avro schemas for type safety and schema evolution.

### Input Events

#### ProfileCreated Event

**Topic**: `profile-events`
**Schema**: `/wall_common/avro/profile_created.avsc`

```json
{
  "event_id": "evt_123456789",
  "timestamp": "2025-01-08T10:30:00Z",
  "event_type": "ProfileCreated",
  "profile_id": "123e4567-e89b-12d3-a456-426614174000",
  "name": "North Wall Section A",
  "height": 25.5,
  "length": 100.0,
  "width": 3.0,
  "ice_thickness": 0.5,
  "created_by": "system"
}
```

**Fields**:
- `profile_id`: Unique identifier for the wall profile
- `height`: Wall height in meters (affects construction time)
- `length`: Wall length in meters
- `width`: Wall width/thickness in meters
- `ice_thickness`: Ice layer thickness in meters
- `created_by`: User or system that created the profile

#### ProfileUpdated Event

**Topic**: `profile-events`
**Schema**: `/wall_common/avro/profile_updated.avsc`

```json
{
  "event_id": "evt_987654321",
  "timestamp": "2025-01-08T10:35:00Z",
  "event_type": "ProfileUpdated",
  "profile_id": "123e4567-e89b-12d3-a456-426614174000",
  "height": 30.0,
  "updated_by": "user123"
}
```

### Output Events

#### SimulationProgress Event

**Topic**: `simulation-events`
**Schema**: `/wall_common/avro/simulation_progress.avsc`

```json
{
  "event_id": "evt_555666777",
  "timestamp": "2025-01-08T10:31:00Z",
  "event_type": "SimulationProgress",
  "profile_id": "123e4567-e89b-12d3-a456-426614174000",
  "day": 1,
  "ice_volume": 150.0,
  "manpower_hours": 8.5,
  "material_cost": 125.75,
  "labor_cost": 340.00,
  "total_cost": 465.75,
  "cumulative_cost": 465.75
}
```

**Fields**:
- `day`: Simulation day (1-365+)
- `ice_volume`: Volume of ice processed on this day (cubic meters)
- `manpower_hours`: Labor hours required
- `material_cost`: Cost of materials for the day
- `labor_cost`: Cost of labor for the day
- `total_cost`: Total cost for this day
- `cumulative_cost`: Running total cost

## Simulation Algorithm

### Daily Construction Calculation

The simulator uses a sophisticated algorithm that considers:

1. **Environmental Factors**
   - Temperature variations (affects ice hardness)
   - Seasonal changes (winter vs summer efficiency)
   - Weather conditions (simulated)

2. **Physical Constraints**
   - Wall height (taller walls require more scaffolding time)
   - Ice thickness (thicker ice takes longer to shape)
   - Wall dimensions (affects material requirements)

3. **Labor Dynamics**
   - Worker fatigue (efficiency decreases over time)
   - Learning curve (efficiency increases with experience)
   - Team size optimization

### Optimization Features

1. **Async Processing**: Non-blocking I/O for Kafka operations
2. **Batch Processing**: Groups events for efficient processing
3. **Connection Pooling**: Reuses Kafka connections
4. **Memory Management**: Streams large simulations

### Monitoring Metrics

The simulator exposes Prometheus metrics:

```http
GET /metrics
```

**Key Metrics**:
- `simulation_events_processed_total`: Total events processed
- `simulation_days_calculated_total`: Total simulation days completed
- `simulation_processing_duration_seconds`: Processing time per event
- `simulation_active_profiles`: Currently active simulations
- `kafka_consumer_lag`: Consumer lag behind Kafka topics

## Configuration

### Environment Variables

```bash
# Kafka Configuration
KAFKA_BOOTSTRAP_SERVERS=localhost:9092
SCHEMA_REGISTRY_URL=http://localhost:8081
PROFILE_EVENTS_TOPIC=profile-events
SIMULATION_EVENTS_TOPIC=simulation-events

# Performance Tuning
MAX_CONCURRENT_SIMULATIONS=50
BATCH_SIZE=100
CONSUMER_POLL_TIMEOUT=1.0

# Simulation Parameters
DEFAULT_SIMULATION_DAYS=365
ENABLE_WEATHER_SIMULATION=true
ENABLE_SEASONAL_EFFECTS=true

# Logging
LOG_LEVEL=INFO
STRUCTURED_LOGGING=true
```

### Docker Configuration

```yaml
# docker-compose.yml excerpt
simulator:
  build:
    context: .
    dockerfile: docker/Dockerfile.simulator
  ports:
    - "8001:8001"
  environment:
    - KAFKA_BOOTSTRAP_SERVERS=kafka:9092
    - SCHEMA_REGISTRY_URL=http://schema-registry:8081
    - LOG_LEVEL=INFO
  depends_on:
    - kafka
    - schema-registry
  restart: unless-stopped
```

## Development

### Running Locally

```bash
# With hot reload
make run-simulator

# Direct FastAPI command
poetry run uvicorn simulator.main:app --host 0.0.0.0 --port 9000 --reload

# With specific config
KAFKA_BOOTSTRAP_SERVERS=localhost:9092 poetry run python simulator/cli.py
```

### Testing

```bash
# Unit tests
poetry run pytest tests/test_simulator.py -v

# Integration tests with Kafka
KAFKA_ENABLED=true poetry run pytest tests/test_simulator.py

# Performance tests
poetry run pytest tests/test_simulator.py -k performance
```

### Mock Mode

For development without Kafka:

```bash
# Enable mock Kafka (default for local development)
USE_MOCK_KAFKA=true make run-simulator
```

Mock mode provides:
- In-memory event processing
- Deterministic simulation results
- No external dependencies
- Faster startup time

## API Endpoints

### Health Check

```http
GET /health
```

**Response**:
```json
{
  "status": "healthy",
  "timestamp": "2025-01-08T10:45:00Z",
  "version": "0.1.0",
  "kafka_connected": true,
  "active_simulations": 12,
  "uptime_seconds": 3600
}
```

### Metrics

```http
GET /metrics
```

Returns Prometheus-formatted metrics for monitoring.

### Debug Endpoints

```http
# List active simulations
GET /debug/simulations

# Get simulation status
GET /debug/simulations/{profile_id}

# Force simulation restart
POST /debug/simulations/{profile_id}/restart
```

## Error Handling

### Event Processing Errors

The simulator handles various error conditions:

1. **Invalid Event Schema**
   - Logs error with event details
   - Sends to dead letter queue
   - Continues processing other events

2. **Calculation Errors**
   - Retries with exponential backoff
   - Falls back to simplified calculation
   - Alerts monitoring system

3. **Kafka Connection Issues**
   - Automatic reconnection
   - Circuit breaker pattern
   - Graceful degradation to mock mode

### Retry Strategy

```python
@retry(
    stop=stop_after_attempt(3),
    wait=wait_exponential(multiplier=1, min=4, max=10),
    retry=retry_if_exception_type(KafkaException)
)
async def process_event(event: ProfileCreated) -> None:
    # Event processing logic
    pass
```

## Performance Tips

### Optimal Configuration

For high-throughput scenarios:

```bash
# Increase concurrent simulations
MAX_CONCURRENT_SIMULATIONS=100

# Larger batch sizes
BATCH_SIZE=500

# Tune Kafka consumer
KAFKA_CONSUMER_MAX_POLL_RECORDS=1000
KAFKA_CONSUMER_FETCH_MIN_BYTES=50000
```

### Scaling Strategies

1. **Horizontal Scaling**
   - Run multiple simulator instances
   - Use Kafka consumer groups for load balancing
   - Partition by profile_id for consistent routing

2. **Vertical Scaling**
   - Increase container CPU/memory limits
   - Tune JVM settings for Kafka client
   - Use faster storage for temporary data

3. **Optimization Techniques**
   - Pre-calculate common values
   - Cache frequently accessed data
   - Use async/await throughout the pipeline
