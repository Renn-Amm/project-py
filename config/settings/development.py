from config.settings.base import *  # noqa: F401, F403

DEBUG = True

SECRET_KEY = "dev-secret-key-not-for-production"

ALLOWED_HOSTS = ["*"]

STATICFILES_DIRS = [BASE_DIR / "static"]  # noqa: F405

# CORS - permissive in dev only
CORS_ALLOW_ALL_ORIGINS = True

# Allow browsable API in development
REST_FRAMEWORK["DEFAULT_RENDERER_CLASSES"] = (  # noqa: F405
    "rest_framework.renderers.JSONRenderer",
    "rest_framework.renderers.BrowsableAPIRenderer",
)
