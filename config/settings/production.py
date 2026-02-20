import os

from typing import Any, cast

import config.settings.base as base_settings

from config.settings.base import *  # noqa: F401, F403

DEBUG = False

SECRET_KEY = os.environ["SECRET_KEY"]

ALLOWED_HOSTS = os.environ.get("ALLOWED_HOSTS", "").split(",")

# Security headers
SECURE_SSL_REDIRECT = True
SECURE_HSTS_SECONDS = 31536000
SECURE_HSTS_INCLUDE_SUBDOMAINS = True
SECURE_HSTS_PRELOAD = True
SECURE_CONTENT_TYPE_NOSNIFF = True
SECURE_BROWSER_XSS_FILTER = True
SESSION_COOKIE_SECURE = True
CSRF_COOKIE_SECURE = True
SESSION_COOKIE_HTTPONLY = True
CSRF_COOKIE_HTTPONLY = True
X_FRAME_OPTIONS = "DENY"
SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")

# CORS - strict in production
CORS_ALLOW_ALL_ORIGINS = False
CORS_ALLOWED_ORIGINS = [
    origin.strip()
    for origin in os.environ.get("CORS_ALLOWED_ORIGINS", "").split(",")
    if origin.strip()
]
CORS_ALLOW_CREDENTIALS = True

# Database SSL
DATABASES["default"]["OPTIONS"] = {  # noqa: F405
    "sslmode": "require",
}

# Caching
CACHES = {
    "default": {
        "BACKEND": "django.core.cache.backends.redis.RedisCache",
        "LOCATION": os.environ.get("REDIS_URL", "redis://localhost:6379/0"),
        "OPTIONS": {
            "ssl_cert_reqs": None,
        },
    }
}

# Tighter throttle rates in production
REST_FRAMEWORK["DEFAULT_THROTTLE_RATES"] = {  # noqa: F405
    "anon": "30/minute",
    "user": "500/minute",
    "evaluation": "2000/minute",
}

# Production logging
logging_config: dict[str, Any] = cast(dict[str, Any], getattr(base_settings, "LOGGING", {}))
handlers: dict[str, Any] = cast(dict[str, Any], logging_config.get("handlers", {}))
root: dict[str, Any] = cast(dict[str, Any], logging_config.get("root", {}))

handlers["file"] = {
    "class": "logging.FileHandler",
    "filename": os.environ.get("LOG_FILE", "/var/log/taskmanager/app.log"),
    "formatter": "structured",  # noqa: F405
}
root["handlers"] = ["console", "file"]

logging_config["handlers"] = handlers
logging_config["root"] = root
LOGGING = logging_config
