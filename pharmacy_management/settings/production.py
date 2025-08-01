# pharmacy_management/settings/production.py
from decouple import Config, RepositoryEnv
from .base import *
import os
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parents[2]  # Go up 3 levels from production.py
ENV_FILE = BASE_DIR / '.env.production'

config = Config(repository=RepositoryEnv(ENV_FILE))

DEBUG = config('DEBUG', cast=bool)
SECRET_KEY = config('SECRET_KEY')

ALLOWED_HOSTS = [host.strip() for host in config('ALLOWED_HOSTS').split(',')]
print("ALLOWED_HOSTS =", ALLOWED_HOSTS)

DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.postgresql',
        'NAME': config('DB_NAME'),
        'USER': config('DB_USER'),
        'PASSWORD': config('DB_PASSWORD'),
        'HOST': config('DB_HOST'),
        'PORT': config('DB_PORT'),
    }
}

# STATIC configuration for AWS
STATICFILES_STORAGE = 'storages.backends.s3boto3.S3Boto3Storage'

# The absolute path to the directory where static files will be collected
STATIC_ROOT = os.path.join(BASE_DIR, 'pharmacy_management', 'staticfiles')


SECURE_HSTS_SECONDS = 31536000
SECURE_HSTS_INCLUDE_SUBDOMAINS = True
SECURE_HSTS_PRELOAD = True

SECURE_SSL_REDIRECT = True
SECURE_PROXY_SSL_HEADER = ('HTTP_X_FORWARDED_PROTO', 'https')

SESSION_COOKIE_SECURE = True
CSRF_COOKIE_SECURE = True

SECURE_CONTENT_TYPE_NOSNIFF = True

SECURE_REFERRER_POLICY = "strict-origin"
