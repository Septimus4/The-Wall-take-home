"""Django app configuration for profiles."""

from django.apps import AppConfig


class ProfilesConfig(AppConfig):
    """Configuration for the profiles app."""

    default_auto_field = "django.db.models.BigAutoField"
    name = "apps.profiles"
    verbose_name = "Wall Profiles"
