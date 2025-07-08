"""
Django management command to monitor database connections.
"""
from typing import Any

from django.core.management.base import BaseCommand

from apps.common.db_utils import ConnectionMonitorMixin, get_connection_info


class Command(BaseCommand, ConnectionMonitorMixin):
    """Monitor database connection usage."""

    help = "Monitor PostgreSQL connection usage and pool status"

    def add_arguments(self, parser: Any) -> None:
        parser.add_argument(
            "--format",
            choices=["table", "json"],
            default="table",
            help="Output format (default: table)",
        )

    def handle(self, *_: Any, **options: Any) -> None:
        try:
            info = get_connection_info()

            if options["format"] == "json":
                import json

                self.stdout.write(json.dumps(info, indent=2))
            else:
                self.display_table_format(info)

        except Exception as e:
            self.stdout.write(self.style.ERROR(f"Error getting connection info: {e}"))

    def display_table_format(self, info: dict[str, Any]) -> None:
        """Display connection info in table format."""
        self.stdout.write(self.style.SUCCESS("\n=== Database Connection Status ==="))

        # Overall stats
        self.stdout.write(f"Max Connections: {info['max_connections']}")
        self.stdout.write(f"Total Connections: {info['total_connections']}")
        self.stdout.write(f"Active Connections: {info['active_connections']}")
        self.stdout.write(f"Idle Connections: {info['idle_connections']}")
        self.stdout.write(f"Utilization: {info['utilization_percent']}%")

        if info["utilization_percent"] > 80:
            self.stdout.write(
                self.style.WARNING("⚠️  High connection utilization detected!")
            )
        elif info["utilization_percent"] > 90:
            self.stdout.write(self.style.ERROR("🚨 Critical connection utilization!"))
        else:
            self.stdout.write(self.style.SUCCESS("✅ Connection utilization is healthy"))

        # By application
        self.stdout.write(self.style.SUCCESS("\n=== Connections by Application ==="))
        for app in info["by_application"]:
            states_str = ", ".join(app["states"]) if app["states"] else "unknown"
            self.stdout.write(
                f"{app['app']}: {app['connections']} connections ({states_str})"
            )
