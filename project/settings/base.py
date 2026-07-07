import os
from pathlib import Path
from celery.schedules import crontab
from django.core.exceptions import ImproperlyConfigured

BASE_DIR = Path(__file__).resolve().parent.parent.parent

CONFIG_ENV_PATH = BASE_DIR / "config.env"
if CONFIG_ENV_PATH.exists():
    with CONFIG_ENV_PATH.open() as env_file:
        for line in env_file:
            line = line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            key, value = line.split("=", 1)
            os.environ[key.strip()] = value.strip()

def get_env_variable(var_name, default=None, required=False):
    """Safely get environment variable, with optional requirement."""
    value = os.environ.get(var_name, default)
    if required and not value:
        raise ImproperlyConfigured(f"Required environment variable '{var_name}' is not set")
    return value

ON_WINDOWS = os.name == "nt"
IN_DOCKER = os.environ.get("IN_DOCKER", "0") == "1"

if ON_WINDOWS:
    VENV_BASE = os.environ.get("VIRTUAL_ENV", os.path.join(BASE_DIR, "venv"))
    OSGEO_PATH = os.path.join(VENV_BASE, "Lib", "site-packages", "osgeo")
    if os.path.exists(OSGEO_PATH):
        os.environ["PATH"] = OSGEO_PATH + ";" + os.environ["PATH"]
        os.environ["PROJ_LIB"] = os.path.join(OSGEO_PATH, "data", "proj")
        GDAL_LIBRARY_PATH = os.path.join(OSGEO_PATH, "gdal.dll")
    else:
        # Fallback to system GDAL installation
        SYSTEM_GDAL_PATH = r"C:\Program Files\GDAL"
        if os.path.exists(SYSTEM_GDAL_PATH):
            if hasattr(os, "add_dll_directory"):
                os.add_dll_directory(SYSTEM_GDAL_PATH)
            os.environ["PATH"] = SYSTEM_GDAL_PATH + ";" + os.environ["PATH"]
            
            proj_lib_path = os.path.join(SYSTEM_GDAL_PATH, "projlib")
            if os.path.exists(proj_lib_path):
                os.environ["PROJ_LIB"] = proj_lib_path
                
            import glob
            dlls = glob.glob(os.path.join(SYSTEM_GDAL_PATH, "gdal*.dll"))
            if dlls:
                GDAL_LIBRARY_PATH = dlls[0]
            else:
                GDAL_LIBRARY_PATH = None
        else:
            GDAL_LIBRARY_PATH = None
else:
    GDAL_LIBRARY_PATH = os.environ.get("GDAL_LIBRARY_PATH", "/usr/lib/x86_64-linux-gnu/libgdal.so.36")

INSTALLED_APPS = [
    'daphne',
    'channels',
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.gis',
    'django.contrib.staticfiles',
    'location_field',
    'home',
    'authentication',
    'supervisor',
    'client',
    'camera_management',
]

MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.locale.LocaleMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
    'whitenoise.middleware.WhiteNoiseMiddleware',
    'authentication.middlewares.MediaCorsMiddleware',
    'authentication.middlewares.SeparateSessionMiddleware',
]

ROOT_URLCONF = 'project.urls'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [os.path.join(BASE_DIR, 'templates')],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.debug',
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
            ],
        },
    },
]

WSGI_APPLICATION = 'project.wsgi.application'
ASGI_APPLICATION = 'project.asgi.application'

AUTH_PASSWORD_VALIDATORS = [
    {'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator'},
    {'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator'},
    {'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator'},
    {'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator'},
]

LANGUAGE_CODE = 'en-us'
TIME_ZONE = 'Africa/Tunis'
USE_I18N = True
USE_TZ = True

LANGUAGES = [
    ('en', 'English'),
    ('fr', 'French'),
    ('ar', 'Arabic'),
]

LOCALE_PATHS = [
    os.path.join(BASE_DIR, 'locale'),
]

STATIC_URL = '/static/'
STATICFILES_DIRS = [os.path.join(BASE_DIR, 'static')]
STATIC_ROOT = os.path.join(BASE_DIR, 'staticfiles')
STATICFILES_STORAGE = 'whitenoise.storage.CompressedManifestStaticFilesStorage'

MEDIA_URL = '/img/'
MEDIA_ROOT = os.path.join(BASE_DIR, 'img/')

DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

EMAIL_BACKEND = 'django.core.mail.backends.smtp.EmailBackend'
EMAIL_HOST = 'smtp.gmail.com'
EMAIL_PORT = 587
EMAIL_USE_TLS = True
EMAIL_HOST_USER = os.environ.get('EMAIL_HOST_USER', '')
EMAIL_HOST_PASSWORD = os.environ.get('EMAIL_HOST_PASSWORD', '')

REDIS_HOST = os.environ.get('REDIS_HOST', 'localhost')
REDIS_PORT = int(os.environ.get('REDIS_PORT', 6379))

CACHES = {
    'default': {
        'BACKEND': 'django_redis.cache.RedisCache',
        'LOCATION': f'redis://{REDIS_HOST}:{REDIS_PORT}/0',
        'OPTIONS': {
            'CLIENT_CLASS': 'django_redis.client.DefaultClient',
        }
    }
}

CHANNEL_LAYERS = {
    'default': {
        'BACKEND': 'channels_redis.core.RedisChannelLayer',
        'CONFIG': {
            'hosts': [(REDIS_HOST, REDIS_PORT)],
        },
    },
}

CELERY_BEAT_SCHEDULE = {
    'predict_fwi_every_5min': {
        'task': 'supervisor.tasks.predict_fwi_for_data',
        'schedule': crontab(minute='*/5'),
    },
}

LOGS_DIR = os.path.join(BASE_DIR, 'logs')
if not os.path.exists(LOGS_DIR):
    os.makedirs(LOGS_DIR, exist_ok=True)

LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'formatters': {
        'verbose': {
            'format': '[{levelname}] {asctime} {name} {funcName}:{lineno} - {message}',
            'style': '{',
            'datefmt': '%Y-%m-%d %H:%M:%S',
        },
    },
    'handlers': {
        'console': {
            'class': 'logging.StreamHandler',
            'formatter': 'verbose',
            'level': 'INFO',
        },
        'file_info': {
            'class': 'logging.handlers.RotatingFileHandler',
            'filename': os.path.join(LOGS_DIR, 'django.log'),
            'maxBytes': 10 * 1024 * 1024,
            'backupCount': 10,
            'formatter': 'verbose',
            'level': 'INFO',
        },
        'file_error': {
            'class': 'logging.handlers.RotatingFileHandler',
            'filename': os.path.join(LOGS_DIR, 'django_errors.log'),
            'maxBytes': 10 * 1024 * 1024,
            'backupCount': 10,
            'formatter': 'verbose',
            'level': 'ERROR',
        },
        'file_celery': {
            'class': 'logging.handlers.RotatingFileHandler',
            'filename': os.path.join(LOGS_DIR, 'celery.log'),
            'maxBytes': 10 * 1024 * 1024,
            'backupCount': 5,
            'formatter': 'verbose',
            'level': 'INFO',
        },
    },
    'loggers': {
        'django': {
            'handlers': ['console', 'file_info', 'file_error'],
            'level': os.environ.get('DJANGO_LOG_LEVEL', 'INFO'),
            'propagate': False,
        },
        'django.request': {
            'handlers': ['console', 'file_error'],
            'level': 'WARNING',
            'propagate': False,
        },
        'django.db.backends': {
            'handlers': ['console'],
            'level': os.environ.get('DB_LOG_LEVEL', 'WARNING'),
            'propagate': False,
        },
        'celery': {
            'handlers': ['console', 'file_celery'],
            'level': os.environ.get('CELERY_LOG_LEVEL', 'INFO'),
            'propagate': False,
        },
        'supervisor': {
            'handlers': ['console', 'file_info', 'file_error'],
            'level': os.environ.get('APP_LOG_LEVEL', 'DEBUG'),
            'propagate': False,
        },
    },
    'root': {
        'handlers': ['console', 'file_info'],
        'level': os.environ.get('ROOT_LOG_LEVEL', 'INFO'),
    },
}
