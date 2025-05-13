# pharmacy_management/settings/__init__.py
import os

env = os.getenv('DJANGO_ENV', 'local')

if env == 'production':
    from .production import *
else:
    from .local import *
