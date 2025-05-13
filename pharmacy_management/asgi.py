# asgi.py
import os

from django.core.asgi import get_asgi_application

environment = os.getenv('DJANGO_ENV', 'local')  # Defaults to 'local' if the variable is not set
os.environ.setdefault('DJANGO_SETTINGS_MODULE', f'pharmacy_management.settings.{environment}')
    

application = get_asgi_application()
