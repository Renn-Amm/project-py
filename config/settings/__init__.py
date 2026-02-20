import os

environment = os.environ.get("DJANGO_ENV", "development").strip().lower()

if environment == "production":
    from config.settings.production import *  # noqa: F401, F403
elif environment == "test":
    from config.settings.test import *  # noqa: F401, F403
else:
    from config.settings.development import *  # noqa: F401, F403
