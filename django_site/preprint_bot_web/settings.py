"""
Django settings for preprint_bot_web project.

Connects to the same PostgreSQL database used by the FastAPI backend.
Uses managed = False on models so Django doesn't try to alter existing tables.
"""

import os
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()

BASE_DIR = Path(__file__).resolve().parent.parent

SECRET_KEY = os.getenv(
    "DJANGO_SECRET_KEY",
    "django-insecure-change-me-in-production-abc123xyz",
)

DEBUG = os.getenv("DJANGO_DEBUG", "True").lower() in ("true", "1", "yes")

ALLOWED_HOSTS = os.getenv("DJANGO_ALLOWED_HOSTS", "localhost,127.0.0.1").split(",")

# ---------------------------------------------------------------------------
# Application definition
# ---------------------------------------------------------------------------

INSTALLED_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "core",
]

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
]

ROOT_URLCONF = "preprint_bot_web.urls"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.debug",
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
                "core.context_processors.date_helpers",
            ],
        },
    },
]

WSGI_APPLICATION = "preprint_bot_web.wsgi.application"

# ---------------------------------------------------------------------------
# Database – points at the existing preprint_bot PostgreSQL database
# ---------------------------------------------------------------------------

DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.postgresql",
        "NAME": os.getenv("DATABASE_NAME", "preprint_bot"),
        "USER": os.getenv("DATABASE_USER", "postgres"),
        "PASSWORD": os.getenv("DATABASE_PASSWORD", ""),
        "HOST": os.getenv("DATABASE_HOST", "localhost"),
        "PORT": os.getenv("DATABASE_PORT", "5432"),
    }
}

# ---------------------------------------------------------------------------
# Authentication — uses PBUser (email-based login via ModelBackend)
# ---------------------------------------------------------------------------

# Where Django auth redirects
LOGIN_URL = "/auth/login/"
LOGIN_REDIRECT_URL = "/"
LOGOUT_REDIRECT_URL = "/auth/login/"

# ---------------------------------------------------------------------------
# Password validation (for Django's own auth – used in admin only)
# ---------------------------------------------------------------------------

AUTH_PASSWORD_VALIDATORS = [
    {"NAME": "django.contrib.auth.password_validation.MinimumLengthValidator"},
]

# ---------------------------------------------------------------------------
# Internationalization
# ---------------------------------------------------------------------------

LANGUAGE_CODE = "en-us"
TIME_ZONE = "America/New_York"
USE_I18N = True
USE_TZ = True

# ---------------------------------------------------------------------------
# Static / Media files
# ---------------------------------------------------------------------------

STATIC_URL = "static/"
STATIC_ROOT = BASE_DIR / "staticfiles"

MEDIA_URL = "media/"
MEDIA_ROOT = BASE_DIR / "media"

# PDF storage paths (mirrors FastAPI config)
PDF_DATA_DIR = Path(os.getenv("PDF_DATA_DIR", BASE_DIR.parent / "pdf_data"))
USER_PDF_DIR = PDF_DATA_DIR / "user_pdfs"
USER_PROCESSED_DIR = PDF_DATA_DIR / "user_processed"

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

# Use our custom user model for Django's auth system
AUTH_USER_MODEL = "core.PBUser"

# ---------------------------------------------------------------------------
# FastAPI backend URL (used for operations that still hit the API)
# ---------------------------------------------------------------------------

FASTAPI_BASE_URL = os.getenv("API_BASE_URL", "http://127.0.0.1:8000")
