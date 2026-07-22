"""
Django settings for crm_project (TechNova CRM).

Config is loaded from a gitignored .env file via django-environ, so secrets
never live in code. Local dev defaults to SQLite; production uses PostgreSQL.
"""
from pathlib import Path
from datetime import timedelta
import environ

# Project root: manage.py lives here
BASE_DIR = Path(__file__).resolve().parent.parent

# Bootstrap .env reader. DEBUG defaults to False if missing.
env = environ.Env(DEBUG=(bool, False))
environ.Env.read_env(str(BASE_DIR / '.env'), overwrite=True)  # force .env over OS vars

# --- Core security ---
SECRET_KEY = env('SECRET_KEY', default='django-insecure-fallback-change-me')  # signing key
DEBUG = env('DEBUG')                                                          # never True in prod
ALLOWED_HOSTS = env.list('ALLOWED_HOSTS', default=['localhost', '127.0.0.1'])


# --- Applications ---
INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'corsheaders',                            # CORS for the React frontend
    'rest_framework',                         # DRF API framework
    'django_filters',                         # filtering for DRF list views
    'accounts.apps.AccountsConfig',           # custom User + profiles
    'crm.apps.CrmConfig',                     # leads, projects, tasks
    'marketing.apps.MarketingConfig',         # public marketing content
]

MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'whitenoise.middleware.WhiteNoiseMiddleware',  # serve static files in production (after Security)
    'corsheaders.middleware.CorsMiddleware',  # must sit high, before CommonMiddleware
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
]

ROOT_URLCONF = 'crm_project.urls'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
            ],
        },
    },
]

WSGI_APPLICATION = 'crm_project.wsgi.application'


# --- Database ---
# DATABASE_URL in .env decides the engine:
#   local dev:  sqlite:///db.sqlite3
#   production: postgres://user:pass@host:5432/dbname
DATABASES = {
    'default': env.db(default='sqlite:///db.sqlite3'),
}

# Point auth at our custom User model (must be set BEFORE first migration)
AUTH_USER_MODEL = 'accounts.User'

# --- Password hashing ---
# Argon2 is the PRIMARY hasher (OWASP recommended, memory-hard, resists GPU/ASIC).
# PBKDF2 is kept as fallback (ships with Django, zero dependencies).
# Existing PBKDF2 passwords auto-upgrade to Argon2 on next login (seamless).
PASSWORD_HASHERS = [
    'django.contrib.auth.hashers.Argon2PasswordHasher',      # primary (new passwords)
    'django.contrib.auth.hashers.PBKDF2PasswordHasher',      # fallback (verify old)
    'django.contrib.auth.hashers.PBKDF2SHA1PasswordHasher',  # legacy fallback
]


# --- Django REST Framework ---
REST_FRAMEWORK = {
    'DEFAULT_AUTHENTICATION_CLASSES': (
        'rest_framework_simplejwt.authentication.JWTAuthentication',  # JWT bearer tokens
    ),
    'DEFAULT_RENDERER_CLASSES': (
        'rest_framework.renderers.JSONRenderer',  # JSON only — NO browsable API HTML
    ),
    'DEFAULT_PERMISSION_CLASSES': (
        'rest_framework.permissions.IsAuthenticated',  # deny by default
    ),
    'DEFAULT_FILTER_BACKENDS': (
        'django_filters.rest_framework.DjangoFilterBackend',  # ?field=value filtering
    ),
    'DEFAULT_THROTTLE_CLASSES': (
        'rest_framework.throttling.AnonRateThrottle',  # limits anonymous traffic
        'rest_framework.throttling.UserRateThrottle',  # limits logged-in traffic
    ),
    'DEFAULT_THROTTLE_RATES': {
        'anon': '30/hour',   # public endpoints (e.g. lead form) anti-spam
        'user': '1000/day',  # authenticated endpoints
    },
}

# --- SimpleJWT token lifecycle + HttpOnly cookie config ---
SIMPLE_JWT = {
    'ACCESS_TOKEN_LIFETIME': timedelta(
        minutes=env.int('DJANGO_SIMPLEJWT_ACCESS_TOKEN_LIFETIME_MINUTES', default=15)),
    'REFRESH_TOKEN_LIFETIME': timedelta(
        days=env.int('DJANGO_SIMPLEJWT_REFRESH_TOKEN_LIFETIME_DAYS', default=7)),
    'AUTH_COOKIE': 'refresh_token',     # cookie name holding the refresh token
    'AUTH_COOKIE_HTTP_ONLY': True,      # JS cannot read it -> XSS mitigation
    'AUTH_COOKIE_SECURE': not DEBUG,    # HTTPS-only in production
    'AUTH_COOKIE_SAMESITE': 'Lax',      # CSRF mitigation
    'AUTH_COOKIE_PATH': '/',
}

# --- CORS & CSRF ---
CORS_ALLOWED_ORIGINS = env.list('CORS_ALLOWED_ORIGINS', default=[
    'http://localhost:5173', 
    'http://127.0.0.1:5173'
])  # React dev server and prod URLs
CORS_ALLOW_CREDENTIALS = True  # allow cookies (refresh token) cross-origin

# --- Production CSRF validation ---
CSRF_TRUSTED_ORIGINS = env.list('CSRF_TRUSTED_ORIGINS', default=[
    'http://localhost:5173', 
    'http://127.0.0.1:5173'
])


# --- Email ---
# Dev: 'console' backend prints mail to the terminal (no provider needed).
# Prod: switch to 'smtp' + fill SMTP_* vars in .env (SendGrid / Brevo / SES).
EMAIL_BACKEND = env('EMAIL_BACKEND', default='django.core.mail.backends.console.EmailBackend')
DEFAULT_FROM_EMAIL = env('DEFAULT_FROM_EMAIL', default='TechNova CRM <noreply@technova.com>')
EMAIL_HOST = env('EMAIL_HOST', default='')          # e.g. smtp.sendgrid.net
EMAIL_PORT = env.int('EMAIL_PORT', default=587)
EMAIL_HOST_USER = env('EMAIL_HOST_USER', default='')
EMAIL_HOST_PASSWORD = env('EMAIL_HOST_PASSWORD', default='')
EMAIL_USE_TLS = env.bool('EMAIL_USE_TLS', default=True)
# NOTE: async sending (Celery+Redis) is wired in Phase 6 behind crm/notify.py


# --- Celery (async task queue) ---
# Dev: CELERY_TASK_ALWAYS_EAGER=True runs tasks synchronously (no Redis needed).
# Prod: set to False + provide CELERY_BROKER_URL pointing to a Redis server.
CELERY_BROKER_URL = env('CELERY_BROKER_URL', default='redis://localhost:6379/0')
CELERY_RESULT_BACKEND = env('CELERY_RESULT_BACKEND', default='redis://localhost:6379/0')
CELERY_TASK_ALWAYS_EAGER = env.bool('CELERY_TASK_ALWAYS_EAGER', default=DEBUG)
CELERY_TASK_EAGER_PROPAGATES = True  # raise exceptions in eager mode (dev debugging)
CELERY_ACCEPT_CONTENT = ['json']
CELERY_TASK_SERIALIZER = 'json'
CELERY_RESULT_SERIALIZER = 'json'
CELERY_TIMEZONE = 'UTC'  # match Django's TIME_ZONE below


# --- Production security (only active when DEBUG=False) ---
if not DEBUG:
    SECURE_SSL_REDIRECT = True          # force HTTPS
    SECURE_HSTS_SECONDS = 2592000        # 30 days: browser remembers to use HTTPS
    SECURE_HSTS_INCLUDE_SUBDOMAINS = True
    SECURE_HSTS_PRELOAD = True
    SECURE_CONTENT_TYPE_NOSNIFF = True   # prevent MIME-type sniffing
    SECURE_BROWSER_XSS_FILTER = True
    SESSION_COOKIE_SECURE = True         # cookies over HTTPS only
    CSRF_COOKIE_SECURE = True
    X_FRAME_OPTIONS = 'DENY'             # prevent clickjacking (no iframe embedding)


# --- Password validation ---
AUTH_PASSWORD_VALIDATORS = [
    {'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator'},
    {'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator'},
    {'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator'},
    {'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator'},
]


# --- Internationalization ---
LANGUAGE_CODE = 'en-us'
TIME_ZONE = 'UTC'
USE_I18N = True
USE_TZ = True


# --- Static files ---
STATIC_URL = 'static/'
STATIC_ROOT = env('STATIC_ROOT', default='staticfiles/')  # collectstatic output dir
# WhiteNoise: long-cache immutable static files in production (no-op in dev)
STORAGES = {
    'default': {'BACKEND': 'django.core.files.storage.FileSystemStorage'},
    'staticfiles': {
        'BACKEND': 'whitenoise.storage.CompressedManifestStaticFilesStorage' if not DEBUG
                   else 'django.contrib.staticfiles.storage.StaticFilesStorage',
    },
}


# --- Logging ---
# Dev: console at INFO. Prod: WARNING+ to file + console.
LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'formatters': {
        'verbose': {
            'format': '{levelname} {asctime} {module} {message}',
            'style': '{',
        },
    },
    'handlers': {
        'console': {
            'class': 'logging.StreamHandler',
            'formatter': 'verbose',
        },
    },
    'root': {
        'handlers': ['console'],
        'level': 'INFO' if DEBUG else 'WARNING',
    },
    'loggers': {
        'django.security': {  # security events (CSRF, permission denied)
            'handlers': ['console'],
            'level': 'WARNING',
            'propagate': False,
        },
        'celery': {
            'handlers': ['console'],
            'level': 'INFO',
            'propagate': False,
        },
    },
}


DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'
