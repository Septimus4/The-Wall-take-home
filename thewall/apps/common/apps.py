"""Django app configuration for common utilities."""

from django.apps import AppConfig


class CommonConfig(AppConfig):
    """Configuration for the common app."""

    default_auto_field = "django.db.models.BigAutoField"
    name = "apps.common"
