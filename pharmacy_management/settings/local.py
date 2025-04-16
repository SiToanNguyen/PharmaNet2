from .base import *

DEBUG = True
SECRET_KEY = 'your-local-dev-secret-key'

ALLOWED_HOSTS = ['localhost', '127.0.0.1']

DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.postgresql',
        'NAME': 'pharmacy_management',
        'USER': 'postgres',
        'PASSWORD': '5987',
        'HOST': '127.0.0.1',
        'PORT': '5432',
    }
}
