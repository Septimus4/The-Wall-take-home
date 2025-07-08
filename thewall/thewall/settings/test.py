"""
Test settings for The Wall project.
"""


from .base import *  # noqa: F403

# Note: DEBUG is controlled via environment variable in base.py
# For tests, you may want to set DEBUG=true in test environment if needed

ALLOWED_HOSTS = ["testserver", "localhost", "127.0.0.1"]

# Database - In-memory SQLite for tests
DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.sqlite3",
        "NAME": ":memory:",
    }
}


# Disable migrations for faster tests
class DisableMigrations:
    def __contains__(self, item: str) -> bool:
        return True

    def __getitem__(self, item: str) -> None:
        return None


MIGRATION_MODULES = DisableMigrations()

# Password hashers - Use fast hasher for tests
PASSWORD_HASHERS = [
    "django.contrib.auth.hashers.MD5PasswordHasher",
]

# Email backend for tests
EMAIL_BACKEND = "django.core.mail.backends.locmem.EmailBackend"

# Cache - Dummy cache for tests
CACHES = {
    "default": {
        "BACKEND": "django.core.cache.backends.dummy.DummyCache",
    }
}

# Logging - Minimal for tests
LOGGING = {
    "version": 1,
    "disable_existing_loggers": False,
    "handlers": {
        "console": {
            "class": "logging.StreamHandler",
        },
    },
    "root": {
        "handlers": ["console"],
        "level": "WARNING",
    },
}

# Disable Kafka for tests
KAFKA_CONFIG = KAFKA_CONFIG.copy()  # noqa: F405
KAFKA_CONFIG["enabled"] = False  # type: ignore[assignment]  # Disable Kafka in tests
