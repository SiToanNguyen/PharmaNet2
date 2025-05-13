# pharmacy_management/settings/production.py
from decouple import Config, RepositoryEnv
from .base import *

config = Config(repository=RepositoryEnv('.env.production'))

DEBUG = config('DEBUG', cast=bool)
SECRET_KEY = config('SECRET_KEY')

ALLOWED_HOSTS = config('ALLOWED_HOSTS').split(',')

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
