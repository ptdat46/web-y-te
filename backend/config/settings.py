import os
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent


# Load local development settings without requiring an extra dotenv package.
def _load_dotenv(path):
    if not path.is_file():
        return
    for line in path.read_text(encoding='utf-8').splitlines():
        line = line.strip()
        if not line or line.startswith('#') or '=' not in line:
            continue
        key, value = line.split('=', 1)
        key = key.strip()
        value = value.strip().strip('"').strip("'")
        os.environ.setdefault(key, value)


_load_dotenv(BASE_DIR.parent / '.env')


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
INSTALLED_APPS = ['daphne', 'django.contrib.auth', 'django.contrib.contenttypes', 'django.contrib.sessions', 'django.contrib.messages', 'django.contrib.staticfiles', 'channels', 'rest_framework', 'rest_framework_simplejwt.token_blacklist', 'corsheaders', 'core', 'catalog', 'accounts', 'doctors', 'care', 'chatbot', 'messaging']
MIDDLEWARE = ['corsheaders.middleware.CorsMiddleware', 'django.middleware.security.SecurityMiddleware', 'django.contrib.sessions.middleware.SessionMiddleware', 'django.middleware.common.CommonMiddleware', 'django.middleware.csrf.CsrfViewMiddleware', 'django.contrib.auth.middleware.AuthenticationMiddleware', 'django.contrib.messages.middleware.MessageMiddleware']
ROOT_URLCONF = 'config.urls'
TEMPLATES = [{'BACKEND': 'django.template.backends.django.DjangoTemplates', 'DIRS': [], 'APP_DIRS': True, 'OPTIONS': {'context_processors': ['django.template.context_processors.request', 'django.contrib.auth.context_processors.auth', 'django.contrib.messages.context_processors.messages']}}]
WSGI_APPLICATION = 'config.wsgi.application'
ASGI_APPLICATION = 'config.asgi.application'
if os.getenv('MYSQL_HOST'):
    DATABASES = {'default': {'ENGINE': 'django.db.backends.mysql', 'NAME': os.getenv('MYSQL_DATABASE', 'healthcare'), 'USER': os.getenv('MYSQL_USER', 'healthcare'), 'PASSWORD': os.getenv('MYSQL_PASSWORD', 'healthcare'), 'HOST': os.environ['MYSQL_HOST'], 'PORT': os.getenv('MYSQL_PORT', '3306')}}
else:
    DATABASES = {'default': {'ENGINE': 'django.db.backends.sqlite3', 'NAME': BASE_DIR / 'db.sqlite3'}}
LANGUAGE_CODE = 'vi'
TIME_ZONE = 'UTC'
USE_I18N = True
USE_TZ = True
STATIC_URL = 'static/'
MEDIA_URL = '/media/'
MEDIA_ROOT = BASE_DIR / 'media'
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
EMAIL_BACKEND = os.getenv('EMAIL_BACKEND', 'django.core.mail.backends.console.EmailBackend' if DEBUG else 'django.core.mail.backends.smtp.EmailBackend')
EMAIL_HOST = os.getenv('EMAIL_HOST', '')
EMAIL_PORT = int(os.getenv('EMAIL_PORT', '587'))
EMAIL_HOST_USER = os.getenv('EMAIL_HOST_USER', '')
EMAIL_HOST_PASSWORD = os.getenv('EMAIL_HOST_PASSWORD', '')
EMAIL_USE_TLS = _env_bool('EMAIL_USE_TLS', '1')
EMAIL_USE_SSL = _env_bool('EMAIL_USE_SSL', '0')
DEFAULT_FROM_EMAIL = os.getenv('DEFAULT_FROM_EMAIL', 'no-reply@localhost')
FRONTEND_URL = os.getenv('FRONTEND_URL', 'http://localhost:5173').rstrip('/')
AUTH_TOKEN_TTL_MINUTES = int(os.getenv('AUTH_TOKEN_TTL_MINUTES', '10'))
if not DEBUG and EMAIL_BACKEND == 'django.core.mail.backends.console.EmailBackend':
    raise RuntimeError('EMAIL_BACKEND must be SMTP in production.')
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
        'auth_sensitive': os.getenv('DRF_AUTH_SENSITIVE_RATE', '5/min'),
        'verification': os.getenv('DRF_VERIFICATION_RATE', '5/min'),
    },
}

# Channels
if os.getenv('CHANNEL_LAYER_REDIS_URL'):
    CHANNEL_LAYERS = {
        'default': {
            'BACKEND': 'channels_redis.core.RedisChannelLayer',
            'CONFIG': {
                'hosts': [os.getenv('CHANNEL_LAYER_REDIS_URL')],
            },
        },
    }
else:
    CHANNEL_LAYERS = {
        'default': {
            'BACKEND': 'channels.layers.InMemoryChannelLayer',
        },
    }

