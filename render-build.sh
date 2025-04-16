#!/usr/bin/env bash

# Exit on error
set -o errexit

# Install dependencies (if needed)
pip install -r requirements.txt

# Run database migrations
python manage.py migrate --settings=pharmacy_management.settings.production

# Collect static files
python manage.py collectstatic --noinput --settings=pharmacy_management.settings.production

# (Optional) Create a default superuser if it doesn't exist
# Replace the values below with your admin email and password
echo "from django.contrib.auth import get_user_model; \
User = get_user_model(); \
User.objects.filter(username='admin').exists() or \
User.objects.create_superuser('admin', 'admin@example.com', 'hsbochum!')" | \
python manage.py shell --settings=pharmacy_management.settings.production
