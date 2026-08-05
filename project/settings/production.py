import os
from django.core.exceptions import ImproperlyConfigured

_REQUIRED_VARS = [
    'DJANGO_SECRET_KEY',
    'DJANGO_ALLOWED_HOSTS',
    'POSTGRES_DB',
    'POSTGRES_USER',
    'POSTGRES_PASSWORD',
    'POSTGRES_HOST',
    'REDIS_HOST',
    'CELERY_BROKER_URL',
    'CELERY_RESULT_BACKEND',
]

for var in _REQUIRED_VARS:
    if not os.environ.get(var):
        raise ImproperlyConfigured(f'Required in production: {var}')

from .base import *

DEBUG = False

SECRET_KEY = os.environ.get('DJANGO_SECRET_KEY')
ALLOWED_HOSTS = [h for h in os.environ.get('DJANGO_ALLOWED_HOSTS', '').split(',') if h]

SECURE_SSL_REDIRECT = False
SECURE_HSTS_SECONDS = 31536000
SECURE_HSTS_INCLUDE_SUBDOMAINS = True
SECURE_HSTS_PRELOAD = True
SESSION_COOKIE_SECURE = True
CSRF_COOKIE_SECURE = True

POSTGRES_DB = os.environ.get('POSTGRES_DB')
POSTGRES_USER = os.environ.get('POSTGRES_USER')
POSTGRES_PASSWORD = os.environ.get('POSTGRES_PASSWORD')
POSTGRES_HOST = os.environ.get('POSTGRES_HOST')
POSTGRES_PORT = os.environ.get('POSTGRES_PORT', '5432')

DATABASES = {
    'default': {
        'ENGINE': 'django.contrib.gis.db.backends.postgis',
        'NAME': POSTGRES_DB,
        'USER': POSTGRES_USER,
        'PASSWORD': POSTGRES_PASSWORD,
        'HOST': POSTGRES_HOST,
        'PORT': POSTGRES_PORT,
    }
}

REDIS_HOST = os.environ.get('REDIS_HOST')
REDIS_PORT = int(os.environ.get('REDIS_PORT', 6379))

CHANNEL_LAYERS['default']['CONFIG']['hosts'] = [(REDIS_HOST, REDIS_PORT)]
CACHES['default']['LOCATION'] = f'redis://{REDIS_HOST}:{REDIS_PORT}/0'

CELERY_BROKER_URL = os.environ.get('CELERY_BROKER_URL')
CELERY_RESULT_BACKEND = os.environ.get('CELERY_RESULT_BACKEND')

CSRF_TRUSTED_ORIGINS = [o for o in os.environ.get('CSRF_TRUSTED_ORIGINS', '').split(',') if o]





