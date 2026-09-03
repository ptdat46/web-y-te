import os
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent


def _env_list(name, default=''):
    """Comma-separated env var -> list of stripped non-empty values."""
    raw = os.getenv(name, default)
    return [value.strip() for value in raw.split(',') if value.strip()]


def _env_bool(name, default='0'):
    return os.getenv(name, default).strip().lower() in ('1', 'true', 'yes', 'on')


DEBUG = _env_bool('DJANGO_DEBUG', '0')

KNOWN_INSECURE_SECRETS = {'dev-only-change-me', 'replace-me'}
SECRET_KEY = os.getenv('DJANGO_SECRET_KEY', '')
if not SECRET_KEY:
    if DEBUG:
        SECRET_KEY = 'dev-only-change-me'
    else:
        raise RuntimeError('DJANGO_SECRET_KEY must be set when DJANGO_DEBUG is not 1.')
if not DEBUG and SECRET_KEY in KNOWN_INSECURE_SECRETS:
    raise RuntimeError('DJANGO_SECRET_KEY is still an insecure default; generate a unique value.')

ALLOWED_HOSTS = _env_list('DJANGO_ALLOWED_HOSTS', 'localhost,127.0.0.1' if DEBUG else '')
if not DEBUG and not ALLOWED_HOSTS:
    raise RuntimeError('DJANGO_ALLOWED_HOSTS must be set when DJANGO_DEBUG is not 1.')

AUTH_USER_MODEL = 'accounts.User'
INSTALLED_APPS = ['django.contrib.auth', 'django.contrib.contenttypes', 'django.contrib.sessions', 'django.contrib.messages', 'django.contrib.staticfiles', 'rest_framework', 'rest_framework_simplejwt.token_blacklist', 'corsheaders', 'core', 'catalog', 'accounts', 'doctors', 'care', 'chatbot']
MIDDLEWARE = ['corsheaders.middleware.CorsMiddleware', 'django.middleware.security.SecurityMiddleware', 'django.contrib.sessions.middleware.SessionMiddleware', 'django.middleware.common.CommonMiddleware', 'django.middleware.csrf.CsrfViewMiddleware', 'django.contrib.auth.middleware.AuthenticationMiddleware', 'django.contrib.messages.middleware.MessageMiddleware']
ROOT_URLCONF = 'config.urls'
TEMPLATES = [{'BACKEND': 'django.template.backends.django.DjangoTemplates', 'DIRS': [], 'APP_DIRS': True, 'OPTIONS': {'context_processors': ['django.template.context_processors.request', 'django.contrib.auth.context_processors.auth', 'django.contrib.messages.context_processors.messages']}}]
WSGI_APPLICATION = 'config.wsgi.application'
DATABASES = {'default': {'ENGINE': 'django.db.backends.mysql', 'NAME': os.getenv('MYSQL_DATABASE', 'healthcare'), 'USER': os.getenv('MYSQL_USER', 'healthcare'), 'PASSWORD': os.getenv('MYSQL_PASSWORD', 'healthcare'), 'HOST': os.getenv('MYSQL_HOST', 'localhost'), 'PORT': os.getenv('MYSQL_PORT', '3306')}}
LANGUAGE_CODE = 'vi'
TIME_ZONE = 'UTC'
USE_I18N = True
USE_TZ = True
STATIC_URL = 'static/'
DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'
CORS_ALLOWED_ORIGINS = _env_list('CORS_ALLOWED_ORIGINS', 'http://localhost:5173,http://127.0.0.1:5173' if DEBUG else '')
CORS_ALLOW_CREDENTIALS = True
CSRF_TRUSTED_ORIGINS = _env_list('CSRF_TRUSTED_ORIGINS', ','.join(CORS_ALLOWED_ORIGINS))
CSRF_COOKIE_SAMESITE = os.getenv('CSRF_COOKIE_SAMESITE', 'Lax')
CSRF_COOKIE_HTTPONLY = False
SESSION_COOKIE_SAMESITE = os.getenv('SESSION_COOKIE_SAMESITE', 'Lax')
SECURE_SSL_REDIRECT = _env_bool('SECURE_SSL_REDIRECT', '0')
SESSION_COOKIE_SECURE = _env_bool('SESSION_COOKIE_SECURE', '0')
CSRF_COOKIE_SECURE = _env_bool('CSRF_COOKIE_SECURE', '0')
SECURE_HSTS_SECONDS = int(os.getenv('SECURE_HSTS_SECONDS', '0'))
SECURE_HSTS_INCLUDE_SUBDOMAINS = SECURE_HSTS_SECONDS > 0
SECURE_HSTS_PRELOAD = SECURE_HSTS_SECONDS > 0

REST_FRAMEWORK = {
    'DEFAULT_AUTHENTICATION_CLASSES': [
        'rest_framework_simplejwt.authentication.JWTAuthentication',
    ],
    'DEFAULT_PERMISSION_CLASSES': [
        'rest_framework.permissions.IsAuthenticated',
    ],
    'DEFAULT_THROTTLE_CLASSES': [
        'rest_framework.throttling.AnonRateThrottle',
        'rest_framework.throttling.UserRateThrottle',
    ],
    'DEFAULT_THROTTLE_RATES': {
        'anon': os.getenv('DRF_ANON_RATE', '30/min'),
        'user': os.getenv('DRF_USER_RATE', '300/min'),
    },
}
