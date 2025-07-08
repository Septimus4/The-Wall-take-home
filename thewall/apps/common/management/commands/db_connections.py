"""
Django management command for database connection monitoring and management.
"""

from typing import Any

from django.core.management.base import BaseCommand

from apps.common.db_utils import (
    ConnectionMonitorMixin,
    close_idle_connections,
    force_close_connections,
    get_connection_info,
    get_connection_pool_info,
)


class Command(BaseCommand, ConnectionMonitorMixin):
    """Management command for database connection operations."""

    help = "Monitor and manage database connections"

    def add_arguments(self, parser: Any) -> None:
        """Add command line arguments."""
        parser.add_argument(
            "--action",
            type=str,
            choices=["status", "health", "close-idle", "force-close", "monitor"],
            default="status",
            help="Action to perform (default: status)",
        )
        parser.add_argument(
            "--watch",
            action="store_true",
            help="Watch mode - continuously monitor connections (use with monitor action)",
        )
        parser.add_argument(
            "--interval",
            type=int,
            default=5,
            help="Interval in seconds for watch mode (default: 5)",
        )

    def handle(self, *_: Any, **options: Any) -> None:
        """Handle the command execution."""
        action = options["action"]

        if action == "status":
            self._show_status()
        elif action == "health":
            self._show_health()
        elif action == "close-idle":
            self._close_idle_connections()
        elif action == "force-close":
            self._force_close_connections()
        elif action == "monitor":
            self._monitor_connections(options)

    def _show_status(self) -> None:
        """Show current connection status."""
        self.stdout.write(self.style.SUCCESS("=== Database Connection Status ==="))
        self.log_connection_info()

        try:
            pool_info = get_connection_pool_info()
            self.stdout.write(
                self.style.SUCCESS("\n=== Connection Pool Configuration ===")
            )
            for alias, info in pool_info.items():
                self.stdout.write(f"{alias}:")
                for key, value in info.items():
                    self.stdout.write(f"  {key}: {value}")
        except Exception as e:
            self.stdout.write(self.style.ERROR(f"Failed to get pool info: {e}"))

    def _show_health(self) -> None:
        """Show detailed health information."""
        self.stdout.write(
            self.style.SUCCESS("=== Database Connection Health Check ===")
        )
        self.log_connection_health()

    def _close_idle_connections(self) -> None:
        """Close idle connections."""
        self.stdout.write("Closing idle connections...")
        try:
            closed_count = close_idle_connections()
            self.stdout.write(
                self.style.SUCCESS(
                    f"Successfully closed {closed_count} idle connections"
                )
            )
            self.log_connection_info()
        except Exception as e:
            self.stdout.write(
                self.style.ERROR(f"Failed to close idle connections: {e}")
            )

    def _force_close_connections(self) -> None:
        """Force close all connections."""
        self.stdout.write(
            self.style.WARNING("Force closing all Django database connections...")
        )
        try:
            closed_count = force_close_connections()
            self.stdout.write(
                self.style.SUCCESS(f"Successfully closed {closed_count} connections")
            )
            self.log_connection_info()
        except Exception as e:
            self.stdout.write(
                self.style.ERROR(f"Failed to force close connections: {e}")
            )

    def _monitor_connections(self, options: dict[str, Any]) -> None:
        """Monitor connections continuously."""
        import time

        interval = options["interval"]
        watch = options["watch"]

        if not watch:
            self._show_health()
            return

        self.stdout.write(
            self.style.SUCCESS(
                f"Monitoring database connections (interval: {interval}s)"
            )
        )
        self.stdout.write("Press Ctrl+C to stop")

        try:
            while True:
                self.stdout.write("\n" + "=" * 50)
                self.stdout.write(f"Timestamp: {time.strftime('%Y-%m-%d %H:%M:%S')}")
                self.log_connection_info()

                try:
                    info = get_connection_info()
                    if info["utilization_percent"] > 90:
                        self.stdout.write(
                            self.style.ERROR(
                                "🚨 CRITICAL: Connection utilization > 90%!"
                            )
                        )
                    elif info["utilization_percent"] > 80:
                        self.stdout.write(
                            self.style.WARNING(
                                "⚠️  WARNING: High connection utilization > 80%"
                            )
                        )
                except Exception as e:
                    self.stdout.write(
                        self.style.ERROR(f"Error getting connection info: {e}")
                    )

                time.sleep(interval)

        except KeyboardInterrupt:
            self.stdout.write("\nMonitoring stopped.")
