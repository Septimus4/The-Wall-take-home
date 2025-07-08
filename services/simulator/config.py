"""Configuration for the simulation service."""

from typing import Any

from pydantic_settings import BaseSettings, SettingsConfigDict


class KafkaConfig(BaseSettings):
    """Kafka configuration."""

    model_config = SettingsConfigDict(env_prefix="KAFKA_")

    bootstrap_servers: str = "localhost:9092"
    consumer_group: str = "wall-simulator"
    profile_topic: str = "wall.profiles"
    simulation_topic: str = "wall.simulation"
    schema_registry_url: str = "http://localhost:8081"

    # Consumer settings
    auto_offset_reset: str = "earliest"
    enable_auto_commit: bool = True
    auto_commit_interval_ms: int = 1000

    # Producer settings
    acks: str = "all"
    retries: int = 3
    batch_size: int = 16384
    linger_ms: int = 10


class SimulatorConfig(BaseSettings):
    """Main simulator configuration."""

    model_config = SettingsConfigDict(env_prefix="SIMULATOR_", case_sensitive=False)

    version: str = "0.1.0"
    environment: str = "development"

    # Simulation settings
    initial_simulation_days: int = 5
    max_simulation_days: int = 365

    # Kafka configuration
    kafka_config: KafkaConfig = KafkaConfig()

    # Logging
    log_level: str = "INFO"
    structured_logging: bool = True

    def __init__(self, **kwargs: Any) -> None:
        super().__init__(**kwargs)
        # Initialize nested configs
        self.kafka_config = KafkaConfig()
