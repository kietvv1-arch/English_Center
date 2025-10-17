"""Base settings for webEnglishCenter (Django 5.2+)."""
from __future__ import annotations

from pathlib import Path
import socket
import environ

BASE_DIR = Path(__file__).resolve().parent.parent.parent

# ---- Env ----
env = environ.Env(
    DEBUG=(bool, False),
)
env_file = BASE_DIR / ".env"
if env_file.exists():
    environ.Env.read_env(env_file)

# Core
SECRET_KEY = env("SECRET_KEY")
DEBUG = env.bool("DEBUG", default=False)
ALLOWED_HOSTS = env.list("ALLOWED_HOSTS", default=[])

# i18n / l10n
LANGUAGE_CODE = env("LANGUAGE_CODE", default="vi")
TIME_ZONE = env("TIME_ZONE", default="Asia/Ho_Chi_Minh")
USE_I18N = True
USE_TZ = True

SITE_ID = env.int("SITE_ID", default=1)

# Apps
INSTALLED_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "django.contrib.sites",
    # Third-party
    "rest_framework",
    "django_filters",
    "import_export",
    "constance",
    "constance.backends.database",
    "simple_history",
    "auditlog",
    "django_celery_beat",
    "django_celery_results",
    "django.contrib.postgres",
    "corsheaders",
    "sass_processor",
    # Optional UX/admin
    "jazzmin",
    # Project
    "main",
]

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "corsheaders.middleware.CorsMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
    "simple_history.middleware.HistoryRequestMiddleware",
]

ROOT_URLCONF = "english_center.urls"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [BASE_DIR / "templates", BASE_DIR / "main" / "templates"],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.debug",
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
            ],
        },
    },
]

WSGI_APPLICATION = "english_center.wsgi.application"
ASGI_APPLICATION = "english_center.asgi.application"

# Database (DATABASE_URL wins; else discrete POSTGRES_*)
db_url = env("DATABASE_URL", default=None)
if db_url:
    import dj_database_url

    default_db = dj_database_url.parse(db_url)
    default_db.setdefault("CONN_MAX_AGE", 60)

    # Allow overriding host/port and connection options when running outside docker-compose.
    if default_db.get("ENGINE", "").endswith("postgresql"):
        options = default_db.setdefault("OPTIONS", {})
        options.setdefault("sslmode", "prefer")
        host_override = env("POSTGRES_HOST", default=None)
        if host_override:
            try:
                socket.getaddrinfo(host_override, None)
            except socket.gaierror:
                host_override = "127.0.0.1"
            default_db["HOST"] = host_override
        port_override = env("POSTGRES_PORT", default=None)
        if port_override:
            default_db["PORT"] = port_override
    DATABASES = {"default": default_db}
else:
    DATABASES = {
        "default": {
            "ENGINE": "django.db.backends.postgresql",
            "NAME": env("POSTGRES_DB", default="postgres"),
            "USER": env("POSTGRES_USER", default="postgres"),
            "PASSWORD": env("POSTGRES_PASSWORD", default="123"),
            "HOST": env("POSTGRES_HOST", default="127.0.0.1"),
            "PORT": env("POSTGRES_PORT", default="5432"),
            "CONN_MAX_AGE": 60,
            "OPTIONS": {"sslmode": "prefer"},
        }
    }

# Password validation
AUTH_PASSWORD_VALIDATORS = [
    {"NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator"},
    {"NAME": "django.contrib.auth.password_validation.MinimumLengthValidator"},
    {"NAME": "django.contrib.auth.password_validation.CommonPasswordValidator"},
    {"NAME": "django.contrib.auth.password_validation.NumericPasswordValidator"},
]

# Static / Media
STATIC_URL = "/static/"
STATIC_ROOT = BASE_DIR / "staticfiles"
STATICFILES_DIRS = [BASE_DIR / "static", BASE_DIR / "main" / "static"]
STATICFILES_FINDERS = [
    "django.contrib.staticfiles.finders.FileSystemFinder",
    "django.contrib.staticfiles.finders.AppDirectoriesFinder",
    "sass_processor.finders.CssFinder",
]
MEDIA_URL = "/media/"
MEDIA_ROOT = BASE_DIR / "media"

SASS_PROCESSOR_ROOT = BASE_DIR / "main" / "static"
SASS_PROCESSOR_INCLUDE_DIRS = [
    BASE_DIR / "main" / "static",
    BASE_DIR / "static",
]
SASS_PROCESSOR_ENABLED = True

# Email
EMAIL_BACKEND = env("EMAIL_BACKEND", default="django.core.mail.backends.console.EmailBackend")
DEFAULT_FROM_EMAIL = env("DEFAULT_FROM_EMAIL", default="no-reply@example.com")

# CORS / CSRF
CORS_ALLOWED_ORIGINS = env.list("CORS_ALLOWED_ORIGINS", default=[])
CSRF_TRUSTED_ORIGINS = env.list("CSRF_TRUSTED_ORIGINS", default=[])

# Caches (Redis recommended)
REDIS_URL = env("REDIS_URL", default=None)
if REDIS_URL:
    CACHES = {
        "default": {
            "BACKEND": "django.core.cache.backends.redis.RedisCache",
            "LOCATION": REDIS_URL,
            "TIMEOUT": 60 * 15,
        }
    }
else:
    CACHES = {"default": {"BACKEND": "django.core.cache.backends.locmem.LocMemCache"}}

# Celery
CELERY_BROKER_URL = env("CELERY_BROKER_URL", default=REDIS_URL or "redis://127.0.0.1:6379/1")
CELERY_RESULT_BACKEND = env("CELERY_RESULT_BACKEND", default=REDIS_URL or "redis://127.0.0.1:6379/2")
CELERY_TIMEZONE = TIME_ZONE
CELERY_TASK_ALWAYS_EAGER = False

# DRF
REST_FRAMEWORK = {
    "DEFAULT_AUTHENTICATION_CLASSES": [
        "rest_framework.authentication.SessionAuthentication",
        "rest_framework.authentication.BasicAuthentication",
    ],
    "DEFAULT_FILTER_BACKENDS": ["django_filters.rest_framework.DjangoFilterBackend"],
    "DEFAULT_PAGINATION_CLASS": "rest_framework.pagination.PageNumberPagination",
    "PAGE_SIZE": 20,
}

# Constance
CONSTANCE_BACKEND = "constance.backends.database.DatabaseBackend"
CONSTANCE_CONFIG = {
    "DEFAULT_TUITION": (0, "Default tuition fee (VND)"),
    "VAT_RATE": (0.0, "VAT rate"),
}

# Logging (compact dev-friendly)
LOGGING = {
    "version": 1,
    "disable_existing_loggers": False,
    "handlers": {
        "console": {"class": "logging.StreamHandler"},
    },
    "root": {"handlers": ["console"], "level": "INFO"},
    "loggers": {
        "django.request": {"handlers": ["console"], "level": "WARNING", "propagate": False},
    },
}

