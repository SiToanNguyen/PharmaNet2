# pharmacy_management/wsgi.py
import os
from django.core.wsgi import get_wsgi_application

# Always use production settings here
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'pharmacy_management.settings.production')

application = get_wsgi_application()
