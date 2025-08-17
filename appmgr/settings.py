import os
from pathlib import Path
from dotenv import load_dotenv
import dj_database_url
import logging

BASE_DIR = Path(__file__).resolve().parent.parent
load_dotenv(BASE_DIR / ".env")

log = logging.getLogger(__name__)

DEBUG = os.getenv("DEBUG", "0").lower() in ("1", "true", "yes")
SECRET_KEY = os.getenv("SECRET_KEY", "dev-not-secret")


def _env_list(name: str, default: str = ""):
    raw = os.getenv(name, default)
    return [p.strip() for p in raw.split(",") if p.strip()]


ALLOWED_HOSTS = _env_list("ALLOWED_HOSTS", "*")

render_host = os.getenv("RENDER_EXTERNAL_HOSTNAME")
if render_host and render_host not in ALLOWED_HOSTS:
    ALLOWED_HOSTS.append(render_host)


def _env_list(name: str, default: str = ""):
    raw = os.getenv(name, default)
    return [p.strip() for p in raw.split(",") if p.strip()]


CSRF_TRUSTED_ORIGINS = _env_list("CSRF_TRUSTED_ORIGINS", "https://grad-app.fly.dev")

SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")
SESSION_COOKIE_SECURE = not DEBUG
CSRF_COOKIE_SECURE = not DEBUG

# --- Apps ---
INSTALLED_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "whitenoise.runserver_nostatic",
    "django.contrib.staticfiles",
    "django.contrib.sites",
    "django_htmx",
    "applications",
    "storages",
    "allauth",
    "allauth.account",
    "allauth.socialaccount",
    "allauth.socialaccount.providers.google",
    "allauth.socialaccount.providers.microsoft",
    "mailwatch",
]

SITE_ID = int(os.getenv("SITE_ID", "1"))

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "whitenoise.middleware.WhiteNoiseMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django_htmx.middleware.HtmxMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
    "allauth.account.middleware.AccountMiddleware",
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

# --- i18n ---
LANGUAGE_CODE = "en-us"
TIME_ZONE = "Asia/Singapore"
USE_I18N = True
USE_TZ = True

# All auth stuff
ACCOUNT_AUTHENTICATION_METHOD = "username_email"
ACCOUNT_EMAIL_REQUIRED = False
ACCOUNT_EMAIL_VERIFICATION = "none"
ACCOUNT_USER_MODEL_USERNAME_FIELD = "username"

AUTHENTICATION_BACKENDS = (
    "django.contrib.auth.backends.ModelBackend",
    "allauth.account.auth_backends.AuthenticationBackend",
)

SOCIALACCOUNT_PROVIDERS = {
    "google": {
        # We need a refresh token → ask for offline access explicitly.
        "APP": {
            "client_id": os.getenv("GOOGLE_CLIENT_ID", ""),
            "secret": os.getenv("GOOGLE_CLIENT_SECRET", ""),
        },
        "SCOPE": [
            "openid",
            "email",
            "profile",
            "https://www.googleapis.com/auth/gmail.readonly",
        ],
        "AUTH_PARAMS": {"access_type": "offline", "prompt": "consent"},
    },
    "microsoft": {
        "APP": {
            "client_id": os.getenv("MS_CLIENT_ID", ""),
            "secret": os.getenv("MS_CLIENT_SECRET", ""),
        },
        # Graph scopes. offline_access is implied, but include for clarity.
        "SCOPE": [
            "openid",
            "email",
            "profile",
            "offline_access",
            "https://graph.microsoft.com/Mail.Read",
        ],
        # You can also set "tenant": "common" (default) or your tenant ID.
        "TENANT": os.getenv("MS_TENANT", "common"),
    },
}

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"
LOGIN_REDIRECT_URL = "applications:dashboard"
LOGOUT_REDIRECT_URL = "applications:dashboard"

# --- Static files (served by WhiteNoise) ---
STATIC_URL = "/static/"
STATIC_ROOT = os.path.join(BASE_DIR, "staticfiles")
STATICFILES_STORAGE = "whitenoise.storage.CompressedManifestStaticFilesStorage"

# --- OpenAI (optional) ---
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "")

# --- AWS S3 for media (attachments) ---
AWS_ACCESS_KEY_ID = os.getenv("AWS_ACCESS_KEY_ID")
AWS_SECRET_ACCESS_KEY = os.getenv("AWS_SECRET_ACCESS_KEY")
AWS_STORAGE_BUCKET_NAME = os.getenv("AWS_STORAGE_BUCKET_NAME")
AWS_S3_REGION_NAME = os.getenv("AWS_S3_REGION_NAME", "ap-southeast-1")
AWS_S3_SIGNATURE_VERSION = "s3v4"
AWS_S3_ADDRESSING_STYLE = "virtual"
AWS_DEFAULT_ACL = None
AWS_S3_FILE_OVERWRITE = False
AWS_QUERYSTRING_AUTH = True
AWS_S3_OBJECT_PARAMETERS = {"ServerSideEncryption": "AES256"}

DEFAULT_FILE_STORAGE = "storages.backends.s3boto3.S3Boto3Storage"
MEDIA_URL = (
    f"https://{AWS_STORAGE_BUCKET_NAME}.s3.amazonaws.com/"
    if AWS_STORAGE_BUCKET_NAME
    else "/media/"
)

# --- Database (Supabase / Postgres via DATABASE_URL) ---
DATABASES = {
    "default": dj_database_url.config(
        env="DATABASE_URL",
        conn_max_age=int(os.getenv("DB_CONN_MAX_AGE", "600")),
        ssl_require=True,
    )
}

_db_url = os.getenv("DATABASE_URL")
if _db_url:
    # Ensure sslmode=require in OPTIONS for Supabase pooler
    DATABASES["default"].setdefault("OPTIONS", {})
    DATABASES["default"]["OPTIONS"]["sslmode"] = "require"

# Debug prints: safe in logs
if _db_url:
    print("DB URL used by Django:", _db_url)
    print("Parsed NAME:", DATABASES["default"].get("NAME"))
    print("Parsed HOST:", DATABASES["default"].get("HOST"))
    print("Parsed PORT:", DATABASES["default"].get("PORT"))
    print("Parsed USER:", DATABASES["default"].get("USER"))


SESSION_COOKIE_SECURE = not DEBUG
CSRF_COOKIE_SECURE = not DEBUG
