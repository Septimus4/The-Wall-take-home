"""
Production settings for The Wall project.
"""

import os

from .base import *  # noqa: F403

# Note: DEBUG is controlled via environment variable in base.py
# In production, ensure DEBUG environment variable is not set or set to false

ALLOWED_HOSTS = os.getenv("ALLOWED_HOSTS", "").split(",")

# Database - PostgreSQL for production
DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.postgresql",
        "NAME": os.getenv("DB_NAME", "wall"),
        "USER": os.getenv("DB_USER", "wall"),
        "PASSWORD": os.getenv("DB_PASSWORD", "wall"),
        "HOST": os.getenv("DB_HOST", "localhost"),
        "PORT": os.getenv("DB_PORT", "5432"),
        "CONN_MAX_AGE": 600,  # Keep connections alive for 10 minutes in production
        # Note: DB_MAX_CONNS environment variable can be used for connection pool monitoring
        # but is not passed to PostgreSQL as it's not a valid psycopg2 connection option
        "OPTIONS": {
            "sslmode": "require",
            "connect_timeout": 10,
            "application_name": f"wall-django-{os.getenv('CONTAINER_NAME', 'production')}",
            # Connection reliability settings
            "keepalives_idle": 600,  # Send keepalive after 10 min of inactivity
            "keepalives_interval": 30,  # Send keepalive every 30 seconds
            "keepalives_count": 3,  # Drop connection after 3 failed keepalives
            # Performance tuning
            "prepared_statement_cache_size": 100,  # Cache prepared statements
        },
    }
}

# Parse DATABASE_URL if provided (for Docker/Cloud deployments)
database_url = os.getenv("DATABASE_URL")
if database_url:
    import dj_database_url

    parsed_db = dj_database_url.parse(database_url)
    DATABASES["default"].update(parsed_db)

# Security settings
SECURE_BROWSER_XSS_FILTER = True
SECURE_CONTENT_TYPE_NOSNIFF = True
SECURE_HSTS_INCLUDE_SUBDOMAINS = True
SECURE_HSTS_SECONDS = 31536000
SECURE_REDIRECT_EXEMPT: list[str] = []
SECURE_SSL_REDIRECT = True
SESSION_COOKIE_SECURE = True
CSRF_COOKIE_SECURE = True
X_FRAME_OPTIONS = "DENY"

# Logging - JSON for production
LOGGING = {
    "version": 1,
    "disable_existing_loggers": False,
    "formatters": {
        "json": {
            "format": '{"time": "%(asctime)s", "level": "%(levelname)s", "name": "%(name)s", "message": "%(message)s"}',
        },
    },
    "handlers": {
        "console": {
            "class": "logging.StreamHandler",
            "formatter": "json",
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
            "level": "INFO",
            "propagate": False,
        },
        "shared": {
            "handlers": ["console"],
            "level": "INFO",
            "propagate": False,
        },
    },
}

# Cache - Redis for production
CACHES = {
    "default": {
        "BACKEND": "django.core.cache.backends.redis.RedisCache",
        "LOCATION": os.getenv("REDIS_URL", "redis://127.0.0.1:6379/1"),
    }
}

# Email backend for production
EMAIL_BACKEND = "django.core.mail.backends.smtp.EmailBackend"
EMAIL_HOST = os.getenv("EMAIL_HOST")
EMAIL_PORT = int(os.getenv("EMAIL_PORT", 587))
EMAIL_USE_TLS = True
EMAIL_HOST_USER = os.getenv("EMAIL_HOST_USER")
EMAIL_HOST_PASSWORD = os.getenv("EMAIL_HOST_PASSWORD")
