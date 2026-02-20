import os

from typing import Any, cast

import config.settings.base as base_settings

from config.settings.base import *  # noqa: F401, F403

DEBUG = False

# WhiteNoise for static files — insert after SecurityMiddleware
MIDDLEWARE.insert(  # noqa: F405
    MIDDLEWARE.index("django.middleware.security.SecurityMiddleware") + 1,  # noqa: F405
    "whitenoise.middleware.WhiteNoiseMiddleware",
)
STORAGES = {
    "staticfiles": {
        "BACKEND": "whitenoise.storage.CompressedManifestStaticFilesStorage",
    },
}

SECRET_KEY = os.environ["SECRET_KEY"]

ALLOWED_HOSTS = os.environ.get("ALLOWED_HOSTS", "").split(",")

CSRF_TRUSTED_ORIGINS = [
    origin.strip()
    for origin in os.environ.get("CSRF_TRUSTED_ORIGINS", "https://*.onrender.com").split(",")
    if origin.strip()
]

# Security headers
SECURE_SSL_REDIRECT = os.environ.get("SECURE_SSL_REDIRECT", "false").lower() == "true"
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

# Database SSL — only enable when the provider supports it
_db_sslmode = os.environ.get("DB_SSLMODE", "")
if _db_sslmode:
    DATABASES["default"]["OPTIONS"] = {  # noqa: F405
        "sslmode": _db_sslmode,
    }

# Caching — use Redis when available, fall back to in-memory
_redis_url = os.environ.get("REDIS_URL")
if _redis_url:
    CACHES = {
        "default": {
            "BACKEND": "django.core.cache.backends.redis.RedisCache",
            "LOCATION": _redis_url,
            "OPTIONS": {
                "ssl_cert_reqs": None,
            },
        }
    }
else:
    CACHES = {
        "default": {
            "BACKEND": "django.core.cache.backends.locmem.LocMemCache",
        }
    }

# Tighter throttle rates in production
REST_FRAMEWORK["DEFAULT_THROTTLE_RATES"] = {  # noqa: F405
    "anon": "30/minute",
    "user": "500/minute",
    "evaluation": "2000/minute",
}

# Production logging — console only (Render has read-only filesystem)
logging_config: dict[str, Any] = cast(dict[str, Any], getattr(base_settings, "LOGGING", {}))
root: dict[str, Any] = cast(dict[str, Any], logging_config.get("root", {}))
root["level"] = "WARNING"
logging_config["root"] = root
LOGGING = logging_config
