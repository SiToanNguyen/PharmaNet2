"""
ASGI config for pharmacy_management project.

It exposes the ASGI callable as a module-level variable named ``application``.

For more information on this file, see
https://docs.djangoproject.com/en/5.1/howto/deployment/asgi/
"""

import os

from django.core.asgi import get_asgi_application

environment = os.getenv('DJANGO_ENV', 'local')  # Defaults to 'local' if the variable is not set
os.environ.setdefault('DJANGO_SETTINGS_MODULE', f'pharmacy_management.settings.{environment}')
    

application = get_asgi_application()
