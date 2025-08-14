import os
from pathlib import Path
from dotenv import load_dotenv
import dj_database_url
import logging


BASE_DIR = Path(__file__).resolve().parent.parent
load_dotenv(BASE_DIR / ".env")
SECRET_KEY = os.getenv("SECRET_KEY", "change-me-in-prod")
DEBUG = os.getenv("DEBUG", "True") == "True"
log = logging.getLogger(__name__)


def _env_list(name: str, default: str = ""):
    raw = os.getenv(name, default)
    parts = [p.strip() for p in raw.split(",") if p.strip()]
    return parts

ALLOWED_HOSTS = _env_list("ALLOWED_HOSTS", "*")

INSTALLED_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "django_htmx",
    "applications",
    "storages",
]

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django_htmx.middleware.HtmxMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
]

ROOT_URLCONF = "appmgr.urls"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [BASE_DIR / "templates"],
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

WSGI_APPLICATION = "appmgr.wsgi.application"
ASGI_APPLICATION = "appmgr.asgi.application"

AUTH_PASSWORD_VALIDATORS = []

LANGUAGE_CODE = "en-us"
TIME_ZONE = "Asia/Singapore"
USE_I18N = True
USE_TZ = True

STATIC_ROOT = BASE_DIR / "staticfiles"
MIDDLEWARE.insert(1, "whitenoise.middleware.WhiteNoiseMiddleware")
STATICFILES_STORAGE = "whitenoise.storage.CompressedManifestStaticFilesStorage"
STATIC_URL = "static/"
STATICFILES_DIRS = [BASE_DIR / "static"]
DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"
LOGIN_REDIRECT_URL = "applications:dashboard"
LOGOUT_REDIRECT_URL = "applications:dashboard"

# CSRF/secure headers for deployments
# Provide explicit list via CSRF_TRUSTED_ORIGINS env (comma‑separated full origins, e.g. https://yourapp.onrender.com)
CSRF_TRUSTED_ORIGINS = _env_list("CSRF_TRUSTED_ORIGINS")
SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")
SESSION_COOKIE_SECURE = not DEBUG
CSRF_COOKIE_SECURE = not DEBUG

# OpenAI config via env vars (optional)
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "")

# AWS S3 Storage Settings
AWS_ACCESS_KEY_ID = os.getenv("AWS_ACCESS_KEY_ID")
AWS_SECRET_ACCESS_KEY = os.getenv("AWS_SECRET_ACCESS_KEY")
AWS_STORAGE_BUCKET_NAME = os.getenv("AWS_STORAGE_BUCKET_NAME")  # e.g., "appmgr-docs"
AWS_S3_REGION_NAME = "ap-southeast-1"  # Singapore region
AWS_S3_SIGNATURE_VERSION = "s3v4"
AWS_S3_ADDRESSING_STYLE = "virtual"
AWS_DEFAULT_ACL = None
AWS_S3_FILE_OVERWRITE = False
AWS_QUERYSTRING_AUTH = True  # presigned URLs for access
AWS_S3_OBJECT_PARAMETERS = {"ServerSideEncryption": "AES256"}  # SSE-S3 encryption

# Store uploaded media files on S3
DEFAULT_FILE_STORAGE = "storages.backends.s3boto3.S3Boto3Storage"
AWS_QUERYSTRING_AUTH = True

# This is where S3 URLs will point (media)
MEDIA_URL = f"https://{AWS_STORAGE_BUCKET_NAME}.s3.amazonaws.com/"

DATABASES = {
    "default": dj_database_url.parse(
        os.getenv("DATABASE_URL"),
        conn_max_age=600,
        ssl_require=True,
    )
}

_db_url = os.getenv("DATABASE_URL")
if _db_url:
    DATABASES["default"] = dj_database_url.parse(
        _db_url,
        conn_max_age=int(os.getenv("DB_CONN_MAX_AGE", "600")),
        ssl_require=True,  # Supabase
    )
    # Ensure psycopg uses SSL even if param is absent
    DATABASES["default"].setdefault("OPTIONS", {})
    DATABASES["default"]["OPTIONS"]["sslmode"] = "require"
# if _db_url:
#     import dj_database_url
#     DATABASES["default"] = dj_database_url.parse(
#         _db_url, conn_max_age=int(os.getenv("DB_CONN_MAX_AGE", "600")), ssl_require=True
#     )
#     DATABASES["default"].setdefault("OPTIONS", {})
#     DATABASES["default"]["OPTIONS"]["sslmode"] = "require"
# else:
#     # Build from discrete vars
#     DB_HOST = os.getenv("DB_HOST")
#     if DB_HOST:  # only switch if you actually provided host
#         DATABASES["default"] = {
#             "ENGINE": "django.db.backends.postgresql",
#             "NAME": os.getenv("DB_NAME", "postgres"),
#             "USER": os.getenv("DB_USER", "postgres"),
#             "PASSWORD": os.getenv("DB_PASSWORD", ""),
#             "HOST": DB_HOST,
#             "PORT": int(os.getenv("DB_PORT", "5432")),
#             "CONN_MAX_AGE": int(os.getenv("DB_CONN_MAX_AGE", "600")),
#             "OPTIONS": {"sslmode": "require"},
#         }

if _db_url:
    print("DB URL used by Django:", _db_url)
    print("Parsed NAME:", DATABASES["default"].get("NAME"))
    print("Parsed HOST:", DATABASES["default"].get("HOST"))
    print("Parsed PORT:", DATABASES["default"].get("PORT"))
    print("Parsed USER:", DATABASES["default"].get("USER"))
