#!/usr/bin/env python3
"""CLI script to run the simulation service."""

import argparse
import logging
import sys
from pathlib import Path

import uvicorn

# Add project root to sys.path to enable absolute imports
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from services.simulator.config import SimulatorConfig  # noqa: E402


def main() -> None:
    """Main entry point for the simulator CLI."""
    parser = argparse.ArgumentParser(description="Wall Simulation Service")
    parser.add_argument("--host", default="0.0.0.0", help="Host to bind to")
    parser.add_argument("--port", type=int, default=9000, help="Port to bind to")
    parser.add_argument("--reload", action="store_true", help="Enable auto-reload")
    parser.add_argument("--log-level", default="info", help="Log level")
    parser.add_argument("--workers", type=int, default=1, help="Number of workers")

    args = parser.parse_args()

    # Load configuration
    config = SimulatorConfig()

    # Set up logging
    logging.basicConfig(level=getattr(logging, args.log_level.upper()))
    logger = logging.getLogger(__name__)

    logger.info(f"Starting Wall Simulation Service {config.version}")
    logger.info(f"Environment: {config.environment}")
    logger.info(f"Kafka Bootstrap Servers: {config.kafka_config.bootstrap_servers}")
    logger.info(f"Listening on: {args.host}:{args.port}")

    # Start the server
    uvicorn.run(
        "services.simulator.main:app",
        host=args.host,
        port=args.port,
        reload=args.reload,
        log_level=args.log_level,
        workers=args.workers if not args.reload else 1,
    )


if __name__ == "__main__":
    main()
