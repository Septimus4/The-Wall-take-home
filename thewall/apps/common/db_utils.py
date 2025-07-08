"""Database utilities for connection management."""

import logging
import time
from contextlib import contextmanager
from typing import TYPE_CHECKING, Any

from django.conf import settings
from django.db import connection, connections

if TYPE_CHECKING:
    pass

logger = logging.getLogger(__name__)


def get_connection_info() -> dict[str, Any]:
    """Get current database connection information."""
    with connection.cursor() as cursor:
        # Get connection count
        cursor.execute(
            """
            SELECT
                count(*) as total_connections,
                count(*) FILTER (WHERE state = 'active') as active_connections,
                count(*) FILTER (WHERE state = 'idle') as idle_connections
            FROM pg_stat_activity
            WHERE datname = current_database()
        """
        )
        conn_stats = cursor.fetchone()

        # Get max connections
        cursor.execute("SHOW max_connections")
        max_conn = cursor.fetchone()[0]

        # Get connections by application
        cursor.execute(
            """
            SELECT
                application_name,
                count(*) as connections,
                array_agg(DISTINCT state) as states
            FROM pg_stat_activity
            WHERE datname = current_database()
            GROUP BY application_name
            ORDER BY connections DESC
        """
        )
        app_connections = cursor.fetchall()

        return {
            "max_connections": int(max_conn),
            "total_connections": conn_stats[0],
            "active_connections": conn_stats[1],
            "idle_connections": conn_stats[2],
            "utilization_percent": round((conn_stats[0] / int(max_conn)) * 100, 2),
            "by_application": [
                {"app": row[0] or "unknown", "connections": row[1], "states": row[2]}
                for row in app_connections
            ],
        }


def get_connection_pool_info() -> dict[str, Any]:
    """Get Django connection pool information."""
    import os

    pool_info = {}

    for alias, db_config in settings.DATABASES.items():
        conn = connections[alias]

        # Get max connections from environment variable (used for monitoring/documentation)
        max_conns = os.getenv("DB_MAX_CONNS", "Not configured")
        conn_max_age = db_config.get("CONN_MAX_AGE", 0)

        pool_info[alias] = {
            "max_connections_per_process": max_conns,
            "connection_max_age_seconds": conn_max_age,
            "engine": db_config.get("ENGINE", "Unknown"),
            "is_usable": conn.is_usable() if hasattr(conn, "is_usable") else "N/A",
        }

    return pool_info


def close_idle_connections() -> int:
    """Close idle Django database connections."""
    closed_count = 0
    for alias in connections:
        conn = connections[alias]
        if hasattr(conn, "close_if_unusable_or_obsolete"):
            try:
                conn.close_if_unusable_or_obsolete()
                closed_count += 1
                logger.info(f"Closed connection for alias: {alias}")
            except Exception as e:
                logger.warning(f"Failed to close connection {alias}: {e}")

    return closed_count


def force_close_connections() -> int:
    """Force close all Django database connections."""
    closed_count = 0
    for alias in connections:
        try:
            connections[alias].close()
            closed_count += 1
            logger.info(f"Force closed connection for alias: {alias}")
        except Exception as e:
            logger.warning(f"Failed to force close connection {alias}: {e}")

    return closed_count


def check_connection_health() -> dict[str, Any]:
    """Check database connection health and pool status."""
    health_info = {
        "timestamp": time.time(),
        "connection_pool_info": get_connection_pool_info(),
        "postgresql_info": None,
        "recommendations": [],
    }

    try:
        pg_info = get_connection_info()
        health_info["postgresql_info"] = pg_info

        # Generate recommendations
        recommendations = []
        utilization = pg_info["utilization_percent"]

        if utilization > 90:
            recommendations.append(
                "CRITICAL: Connection utilization > 90%. Consider increasing max_connections or implementing connection pooling."
            )
        elif utilization > 80:
            recommendations.append(
                "WARNING: High connection utilization > 80%. Monitor closely and consider optimization."
            )
        elif utilization > 60:
            recommendations.append(
                "CAUTION: Moderate connection utilization > 60%. Consider reviewing connection patterns."
            )

        # Check for idle connections
        if pg_info["idle_connections"] > pg_info["active_connections"] * 2:
            recommendations.append(
                "INFO: High number of idle connections. Consider reducing CONN_MAX_AGE."
            )

        health_info["recommendations"] = recommendations

    except Exception as e:
        logger.error(f"Failed to get PostgreSQL connection info: {e}")
        health_info["postgresql_info"] = {"error": str(e)}

    return health_info


@contextmanager
def connection_monitor(operation_name: str = "operation") -> Any:
    """Context manager to monitor database connections during operations."""
    start_info = None
    try:
        start_info = get_connection_info()
        logger.info(
            f"Starting {operation_name} - DB connections: {start_info['total_connections']}/{start_info['max_connections']}"
        )
        yield
    except Exception as e:
        logger.error(f"Error during {operation_name}: {e}")
        raise
    finally:
        try:
            end_info = get_connection_info()
            if start_info:
                connection_diff = (
                    end_info["total_connections"] - start_info["total_connections"]
                )
                logger.info(
                    f"Completed {operation_name} - DB connections: {end_info['total_connections']}/{end_info['max_connections']} "
                    f"(change: {connection_diff:+d})"
                )
        except Exception as e:
            logger.warning(
                f"Failed to log final connection info for {operation_name}: {e}"
            )


def ensure_connection_cleanup() -> None:
    """Ensure proper connection cleanup (call in signal handlers)."""
    try:
        connections.close_all()
        logger.info("All database connections closed successfully")
    except Exception as e:
        logger.error(f"Error closing database connections: {e}")


class ConnectionMonitorMixin:
    """Mixin for Django management commands to monitor connections."""

    def log_connection_info(self) -> None:
        """Log current connection information."""
        from django.core.management.base import BaseCommand

        if not isinstance(self, BaseCommand):
            raise TypeError(
                "ConnectionMonitorMixin should only be used with BaseCommand"
            )

        try:
            info = get_connection_info()
            self.stdout.write(
                self.style.SUCCESS(
                    f"DB Connections: {info['total_connections']}/{info['max_connections']} "
                    f"({info['utilization_percent']}% utilization)"
                )
            )

            if info["utilization_percent"] > 80:
                self.stdout.write(
                    self.style.WARNING(
                        "High connection utilization! Consider connection pooling."
                    )
                )

        except Exception as e:
            self.stdout.write(self.style.ERROR(f"Failed to get connection info: {e}"))

    def log_connection_health(self) -> None:
        """Log detailed connection health information."""
        from django.core.management.base import BaseCommand

        if not isinstance(self, BaseCommand):
            raise TypeError(
                "ConnectionMonitorMixin should only be used with BaseCommand"
            )

        try:
            health = check_connection_health()

            # Log pool info
            self.stdout.write(self.style.SUCCESS("=== Connection Pool Info ==="))
            for alias, pool_info in health["connection_pool_info"].items():
                self.stdout.write(f"{alias}: {pool_info}")

            # Log PostgreSQL info
            if health["postgresql_info"] and "error" not in health["postgresql_info"]:
                pg_info = health["postgresql_info"]
                self.stdout.write(
                    self.style.SUCCESS("=== PostgreSQL Connection Info ===")
                )
                self.stdout.write(
                    f"Total: {pg_info['total_connections']}/{pg_info['max_connections']} ({pg_info['utilization_percent']}%)"
                )
                self.stdout.write(
                    f"Active: {pg_info['active_connections']}, Idle: {pg_info['idle_connections']}"
                )

            # Log recommendations
            if health["recommendations"]:
                self.stdout.write(self.style.WARNING("=== Recommendations ==="))
                for rec in health["recommendations"]:
                    if rec.startswith("CRITICAL"):
                        self.stdout.write(self.style.ERROR(rec))
                    elif rec.startswith("WARNING"):
                        self.stdout.write(self.style.WARNING(rec))
                    else:
                        self.stdout.write(rec)

        except Exception as e:
            self.stdout.write(
                self.style.ERROR(f"Failed to get connection health info: {e}")
            )
