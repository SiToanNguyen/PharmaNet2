"""
WSGI config for pharmacy_management project.

It exposes the WSGI callable as a module-level variable named ``application``.

For more information on this file, see
https://docs.djangoproject.com/en/5.1/howto/deployment/wsgi/
"""

import os

from django.core.wsgi import get_wsgi_application

environment = os.getenv('DJANGO_ENV', 'local')  # Defaults to 'local' if the variable is not set
os.environ.setdefault('DJANGO_SETTINGS_MODULE', f'pharmacy_management.settings.{environment}')
    

application = get_wsgi_application()
