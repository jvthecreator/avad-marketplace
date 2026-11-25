import os
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent

SECRET_KEY = 'avad-dev-secret-key-change-in-production-2026'

DEBUG = True

ALLOWED_HOSTS = ['*']

INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'django.contrib.humanize',
    'accounts',
    'catalog',
    'orders',
    'finance',
    'disputes',
    'dashboard',
    'notifications',
    'api',
]

MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'whitenoise.middleware.WhiteNoiseMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
    'accounts.middleware.RoleAccessMiddleware',
]

ROOT_URLCONF = 'avad_marketplace.urls'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [BASE_DIR / 'templates'],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.debug',
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
                'orders.context_processors.cart_count',
                'notifications.context_processors.notificacoes',
            ],
        },
    },
]

WSGI_APPLICATION = 'avad_marketplace.wsgi.application'

def _banco_a_partir_da_url(url):
    """Converte uma URL do Postgres (ex.: a "connection string" do Neon) na configuração do Django.
    Formato: postgresql://usuario:senha@host:porta/banco?sslmode=require"""
    from urllib.parse import urlsplit, unquote, parse_qsl
    partes = urlsplit(url)
    if partes.scheme not in ('postgres', 'postgresql'):
        raise ValueError('DATABASE_URL precisa começar com postgresql:// ou postgres://')
    return {
        'ENGINE': 'django.db.backends.postgresql',
        'NAME': unquote(partes.path.lstrip('/')),
        'USER': unquote(partes.username or ''),
        'PASSWORD': unquote(partes.password or ''),
        'HOST': partes.hostname or '',
        'PORT': str(partes.port or ''),
        'OPTIONS': dict(parse_qsl(partes.query)),  # ex.: sslmode=require, channel_binding=require
        'CONN_MAX_AGE': 60,          # reaproveita a conexão por até 60 s
        'CONN_HEALTH_CHECKS': True,  # reconecta se o banco tiver "dormido" (o Neon pausa quando fica ocioso)
    }


# Com a variável DATABASE_URL definida (no Render), usa o Postgres externo, que não é apagado quando o
# site reinicia. Sem ela (no seu computador), continua usando o SQLite local.
if os.environ.get('DATABASE_URL'):
    DATABASES = {'default': _banco_a_partir_da_url(os.environ['DATABASE_URL'])}
else:
    DATABASES = {
        'default': {
            'ENGINE': 'django.db.backends.sqlite3',
            'NAME': BASE_DIR / 'db.sqlite3',
        }
    }


CSRF_TRUSTED_ORIGINS = [
    'https://warren-wto-wars-east.trycloudflare.com',
    'https://*.trycloudflare.com',  # Útil se a URL mudar a cada reinício do túnel
]

AUTH_PASSWORD_VALIDATORS = []

LANGUAGE_CODE = 'pt-br'
TIME_ZONE = 'America/Sao_Paulo'
USE_I18N = True
USE_TZ = True

STATIC_URL = '/static/'
STATICFILES_DIRS = [BASE_DIR / 'static']
STATIC_ROOT = BASE_DIR / 'staticfiles'
STATICFILES_STORAGE = 'whitenoise.storage.CompressedManifestStaticFilesStorage'

MEDIA_URL = '/media/'
MEDIA_ROOT = BASE_DIR / 'media'

DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

LOGIN_URL = '/accounts/login/'
LOGIN_REDIRECT_URL = '/'

# Max upload size 10MB
DATA_UPLOAD_MAX_MEMORY_SIZE = 10 * 1024 * 1024
FILE_UPLOAD_MAX_MEMORY_SIZE = 10 * 1024 * 1024