from config.settings.base import *  # noqa: F401, F403

DEBUG = False

SECRET_KEY = "test-secret-key-for-ci-only"

ALLOWED_HOSTS = ["*"]

# Prefer DATABASE_URL-based config from base settings. This keeps local and CI
# consistent (e.g. docker-compose postgres) while still providing a sane
# fallback for contributors.
if not os.environ.get("DATABASE_URL"):
    DATABASES = {
        "default": {
            "ENGINE": "django.db.backends.postgresql",
            "NAME": "test_featureflags",
            "USER": "postgres",
            "PASSWORD": "postgres",
            "HOST": "localhost",
            "PORT": "5432",
            "TEST": {
                "NAME": "test_featureflags",
            },
        }
    }

# Disable throttling in tests
REST_FRAMEWORK["DEFAULT_THROTTLE_CLASSES"] = []  # noqa: F405
REST_FRAMEWORK["DEFAULT_THROTTLE_RATES"] = {
    "evaluation": "100000/minute",
}  # noqa: F405

# Faster password hashing in tests
PASSWORD_HASHERS = [
    "django.contrib.auth.hashers.MD5PasswordHasher",
]

CACHES = {
    "default": {
        "BACKEND": "django.core.cache.backends.locmem.LocMemCache",
    }
}

CORS_ALLOW_ALL_ORIGINS = True
