"""Dev settings that extend base."""

from .base import *  # noqa: F401,F403
from .base import (
    INSTALLED_APPS as BASE_INSTALLED_APPS,
    MIDDLEWARE as BASE_MIDDLEWARE,
    env,
)

DEBUG = True

ALLOWED_HOSTS = ["localhost", "127.0.0.1", "[::1]"]
CSRF_TRUSTED_ORIGINS = ["http://localhost:8000", "http://127.0.0.1:8000"]

EMAIL_BACKEND = env(
    "EMAIL_BACKEND", default="django.core.mail.backends.console.EmailBackend"
)

# Speed up password hashing in dev (optional)
PASSWORD_HASHERS = [
    "django.contrib.auth.hashers.MD5PasswordHasher",
]

# Copy lists so local tweaks do not mutate base module state.
INSTALLED_APPS = [*BASE_INSTALLED_APPS]
MIDDLEWARE = [*BASE_MIDDLEWARE]

# Django toolbar (optional)
try:
    __import__("debug_toolbar")
except ImportError:
    pass
else:
    INSTALLED_APPS.append("debug_toolbar")
    MIDDLEWARE.insert(0, "debug_toolbar.middleware.DebugToolbarMiddleware")
    INTERNAL_IPS = ["127.0.0.1"]
