"""Health check views."""

import time
from typing import Any

from django.db import connection
from django.http import HttpRequest, JsonResponse


def health_check(_request: HttpRequest) -> JsonResponse:
    """Basic health check endpoint."""
    return JsonResponse(
        {"status": "healthy", "timestamp": time.time(), "service": "api-gateway"}
    )


def readiness_check(_request: HttpRequest) -> JsonResponse:
    """Readiness check that verifies dependencies."""
    checks: dict[str, Any] = {}

    # Check database
    try:
        with connection.cursor() as cursor:
            cursor.execute("SELECT 1")
        checks["database"] = "healthy"
    except Exception as e:
        checks["database"] = f"error: {str(e)}"

    # Check Kafka (basic connectivity)
    try:
        from apps.profiles.kafka_publisher import get_kafka_publisher

        publisher = get_kafka_publisher()
        checks["kafka"] = "healthy" if publisher.producer else "unavailable"
    except Exception as e:
        checks["kafka"] = f"error: {str(e)}"

    all_healthy = all(status == "healthy" for status in checks.values())

    return JsonResponse(
        {
            "status": "ready" if all_healthy else "not_ready",
            "checks": checks,
            "timestamp": time.time(),
            "service": "api-gateway",
        },
        status=200 if all_healthy else 503,
    )
