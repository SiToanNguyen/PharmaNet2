# wsgi.py
import os

from django.core.wsgi import get_wsgi_application

environment = os.getenv('DJANGO_ENV', 'local')  # Defaults to 'local' if the variable is not set
os.environ.setdefault('DJANGO_SETTINGS_MODULE', f'pharmacy_management.settings.{environment}')
    

application = get_wsgi_application()
