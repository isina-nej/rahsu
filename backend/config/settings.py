"""Settings for the research MVP. Secrets must be injected, never committed."""

import os
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
SECRET_KEY = os.getenv("DJANGO_SECRET_KEY", "dev-only-unsafe-do-not-use-in-production")
DEBUG = os.getenv("DJANGO_DEBUG", "0") == "1"
if not DEBUG and SECRET_KEY.startswith("dev-only"):
    # Fail closed on production boot, not during pure-domain imports.
    raise RuntimeError("Set DJANGO_SECRET_KEY before starting production")
ALLOWED_HOSTS = [x.strip() for x in os.getenv("DJANGO_ALLOWED_HOSTS", "localhost,127.0.0.1").split(",") if x.strip()]
INSTALLED_APPS = [
    "django.contrib.admin", "django.contrib.auth", "django.contrib.contenttypes",
    "django.contrib.sessions", "django.contrib.messages", "django.contrib.staticfiles",
    "django.contrib.gis", "rest_framework", "drf_spectacular", "corsheaders",
    "apps.vehicles", "apps.geo", "apps.routing", "apps.fuel",
    "apps.operations.apps.OperationsConfig", "apps.calibration",
]
MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "whitenoise.middleware.WhiteNoiseMiddleware",
    "corsheaders.middleware.CorsMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
    "apps.operations.middleware.RequestContextMiddleware",
]
ROOT_URLCONF = "config.urls"
TEMPLATES = [{"BACKEND": "django.template.backends.django.DjangoTemplates", "DIRS": [],
              "APP_DIRS": True, "OPTIONS": {"context_processors": [
                  "django.template.context_processors.debug", "django.template.context_processors.request",
                  "django.contrib.auth.context_processors.auth", "django.contrib.messages.context_processors.messages"]}}]
WSGI_APPLICATION = "config.wsgi.application"
ASGI_APPLICATION = "config.asgi.application"
DATABASES = {"default": {
    "ENGINE": "django.contrib.gis.db.backends.postgis",
    "NAME": os.getenv("POSTGRES_DB", "rahsu"),
    "USER": os.getenv("POSTGRES_USER", "rahsu"),
    "PASSWORD": os.getenv("POSTGRES_PASSWORD", ""),
    "HOST": os.getenv("POSTGRES_HOST", "localhost"),
    "PORT": os.getenv("POSTGRES_PORT", "5432"),
    "CONN_MAX_AGE": 60,
}}
AUTH_PASSWORD_VALIDATORS = [
    {"NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator"},
    {"NAME": "django.contrib.auth.password_validation.MinimumLengthValidator"},
    {"NAME": "django.contrib.auth.password_validation.CommonPasswordValidator"},
    {"NAME": "django.contrib.auth.password_validation.NumericPasswordValidator"},
]
LANGUAGE_CODE = "fa-ir"
TIME_ZONE = "Asia/Tehran"
USE_I18N = True
USE_TZ = True
STATIC_URL = "/static/"
STORAGES = {"staticfiles":{"BACKEND":"whitenoise.storage.CompressedManifestStaticFilesStorage"}}
STATIC_ROOT = BASE_DIR / "staticfiles"
DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"
CORS_ALLOWED_ORIGINS = [x.strip() for x in os.getenv("DJANGO_CORS_ORIGINS", "http://localhost:5173").split(",") if x.strip()]
REST_FRAMEWORK = {
    "DEFAULT_AUTHENTICATION_CLASSES": ["rest_framework.authentication.SessionAuthentication"],
    "DEFAULT_PERMISSION_CLASSES": ["rest_framework.permissions.AllowAny"],
    "DEFAULT_SCHEMA_CLASS": "drf_spectacular.openapi.AutoSchema",
    "DEFAULT_THROTTLE_CLASSES": ["rest_framework.throttling.AnonRateThrottle", "rest_framework.throttling.UserRateThrottle"],
    "DEFAULT_THROTTLE_RATES": {"anon": "60/hour", "user": "600/hour", "auth":"10/hour"},
}
SPECTACULAR_SETTINGS = {"TITLE": "راه‌سو API", "DESCRIPTION": "Tehran Pride fuel estimate research API", "VERSION": "0.1.0"}
SESSION_COOKIE_SECURE = not DEBUG
CSRF_COOKIE_SECURE = not DEBUG
SECURE_CONTENT_TYPE_NOSNIFF = True
SECURE_REFERRER_POLICY = "same-origin"
X_FRAME_OPTIONS = "DENY"
OSRM_BASE_URL = os.getenv("OSRM_BASE_URL", "http://localhost:5000").rstrip("/")
ELEVATION_BASE_URL = os.getenv("ELEVATION_BASE_URL", "").rstrip("/")
GEOCODER_BASE_URL = os.getenv("GEOCODER_BASE_URL", "").rstrip("/")
LOKI_BASE_URL = os.getenv("LOKI_BASE_URL", "http://localhost:3100").rstrip("/")
PROMETHEUS_BASE_URL = os.getenv("PROMETHEUS_BASE_URL", "").rstrip("/")
TEMPO_BASE_URL = os.getenv("TEMPO_BASE_URL", "").rstrip("/")
CELERY_BROKER_URL = os.getenv("REDIS_URL", "redis://localhost:6379/0")
CELERY_RESULT_BACKEND = CELERY_BROKER_URL
CELERY_TASK_SERIALIZER = "json"
CELERY_ACCEPT_CONTENT = ["json"]
CELERY_RESULT_SERIALIZER = "json"
CELERY_TASK_TIME_LIMIT = 60
CELERY_TASK_SOFT_TIME_LIMIT = 50
LOGGING = {"version": 1, "disable_existing_loggers": False,
           "formatters": {"json": {"()": "apps.operations.logging.JsonFormatter"}},
           "handlers": {"console": {"class": "logging.StreamHandler", "formatter": "json"}},
           "root": {"handlers": ["console"], "level": os.getenv("LOG_LEVEL", "INFO")}}

# Shared Redis cache makes geocoder throttling work across Gunicorn workers.
if os.getenv("REDIS_URL"):
    CACHES={"default":{"BACKEND":"django.core.cache.backends.redis.RedisCache",
                      "LOCATION":os.environ["REDIS_URL"]}}
CSRF_TRUSTED_ORIGINS = [x.strip() for x in os.getenv(
    "DJANGO_CSRF_TRUSTED_ORIGINS",
    "http://localhost:5173,http://localhost:8080").split(",") if x.strip()]
# Trust forwarded HTTPS only when the app is behind an operator-managed proxy.
if os.getenv("TRUST_REVERSE_PROXY") == "1":
    SECURE_PROXY_SSL_HEADER=("HTTP_X_FORWARDED_PROTO","https")
