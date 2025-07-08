"""
Local development settings for The Wall project.
"""

import os
import sys

from .base import *  # noqa: F403

# Note: DEBUG is controlled via environment variable in base.py
# Set DEBUG=true in your environment for local development

ALLOWED_HOSTS = ["localhost", "127.0.0.1", "[::1]", "api"]

# Database configuration - PostgreSQL when USE_SQLITE=False, SQLite otherwise
use_sqlite = os.getenv("USE_SQLITE", "True").lower() in ("true", "1", "yes", "on")

if use_sqlite:
    # SQLite for local development
    DATABASES = {
        "default": {
            "ENGINE": "django.db.backends.sqlite3",
            "NAME": BASE_DIR / "db.sqlite3",  # noqa: F405
        }
    }
else:
    # PostgreSQL for Docker/production-like environments
    DATABASES = {
        "default": {
            "ENGINE": "django.db.backends.postgresql",
            "NAME": os.getenv("DB_NAME", "wall"),
            "USER": os.getenv("DB_USER", "wall"),
            "PASSWORD": os.getenv("DB_PASSWORD", "wall"),
            "HOST": os.getenv("DB_HOST", "postgres"),
            "PORT": os.getenv("DB_PORT", "5432"),
            "CONN_MAX_AGE": 300,  # Keep connections alive for 5 minutes
            # Note: DB_MAX_CONNS environment variable can be used for connection pool monitoring
            # but is not passed to PostgreSQL as it's not a valid psycopg2 connection option
            "OPTIONS": {
                "connect_timeout": 10,
                "application_name": f"wall-django-{os.getenv('CONTAINER_NAME', 'local')}",
                # Additional connection options for reliability
                "keepalives_idle": 600,  # Send keepalive after 10 min of inactivity
                "keepalives_interval": 30,  # Send keepalive every 30 seconds
                "keepalives_count": 3,  # Drop connection after 3 failed keepalives
            },
        }
    }

if "test" in sys.argv:
    DATABASES["default"] = {
        "ENGINE": "django.db.backends.sqlite3",
        "NAME": ":memory:",
    }

# Logging - Verbose for development
LOGGING = {
    "version": 1,
    "disable_existing_loggers": False,
    "formatters": {
        "verbose": {
            "format": "{levelname} {asctime} {module} {process:d} {thread:d} {message}",
            "style": "{",
        },
        "simple": {
            "format": "{levelname} {message}",
            "style": "{",
        },
    },
    "handlers": {
        "console": {
            "class": "logging.StreamHandler",
            "formatter": "verbose",
        },
    },
    "root": {
        "handlers": ["console"],
        "level": "INFO",
    },
    "loggers": {
        "django": {
            "handlers": ["console"],
            "level": "INFO",
            "propagate": False,
        },
        "thewall": {
            "handlers": ["console"],
            "level": "DEBUG",
            "propagate": False,
        },
        "shared": {
            "handlers": ["console"],
            "level": "DEBUG",
            "propagate": False,
        },
    },
}

# Development-specific DRF settings
REST_FRAMEWORK.update(  # noqa: F405
    {
        "DEFAULT_RENDERER_CLASSES": [
            "rest_framework.renderers.JSONRenderer",
            "rest_framework.renderers.BrowsableAPIRenderer",  # Enable DRF browsable API
        ],
    }
)

# Email backend for development
EMAIL_BACKEND = "django.core.mail.backends.console.EmailBackend"

# Cache - Dummy cache for development
CACHES = {
    "default": {
        "BACKEND": "django.core.cache.backends.dummy.DummyCache",
    }
}
