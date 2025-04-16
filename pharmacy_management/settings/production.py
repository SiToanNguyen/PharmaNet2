from .base import *
import dj_database_url

DEBUG = False
SECRET_KEY = os.environ.get("SECRET_KEY", "fallback-production-secret-key")
ALLOWED_HOSTS = ['pharmanet2.onrender.com']

DATABASES = {
    'default': dj_database_url.config(conn_max_age=600)
}
