# pharmacy_management/settings/production.py
from .base import *
import dj_database_url

print("Django is using PRODUCTION settings")

# SECURITY: Use environment variables for sensitive keys in production
DEBUG = False
SECRET_KEY = os.environ.get("SECRET_KEY", "fallback-production-secret-key")  # Preferably stored as an environment variable

ALLOWED_HOSTS = ['16.16.217.97']

# Database: Connect to AWS PostgreSQL database
DATABASES = {
    'default': dj_database_url.config(
        default='postgres://pharmanetuser:your_strong_password@16.16.217.97:5432/pharmanetdb',
        conn_max_age=600
    )
}

# STATIC configuration for AWS
STATIC_ROOT = os.path.join(BASE_DIR, 'staticfiles')
STATICFILES_STORAGE = 'whitenoise.storage.CompressedManifestStaticFilesStorage'

# Secure the app in production
SECURE_SSL_REDIRECT = False  # Redirect HTTP to HTTPS

# Set environment-specific keys for better security management
# Make sure AWS instance has SECRET_KEY and other environment variables configured

print("### Using production settings ###")
