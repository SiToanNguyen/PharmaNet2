# pharmacy_management/settings/production.py
from .base import *
import dj_database_url

DEBUG = False
SECRET_KEY = os.environ.get("SECRET_KEY", "fallback-production-secret-key")

ALLOWED_HOSTS = ['16.16.217.97', '16.16.217.97:8000']

DATABASES = {
    'default': dj_database_url.config(
        default='postgres://pharmanetuser:your_strong_password@16.16.217.97:5432/pharmanetdb',
        conn_max_age=600
    )
}

STATIC_ROOT = os.path.join(BASE_DIR, 'staticfiles')
STATICFILES_STORAGE = 'whitenoise.storage.CompressedManifestStaticFilesStorage'

SECURE_SSL_REDIRECT = False
