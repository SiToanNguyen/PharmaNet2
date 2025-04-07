import os
import django

# Set up the Django environment
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'pharmacy_management.settings')
django.setup()

from django.contrib.auth.models import User

def print_users_and_passwords():
    users = User.objects.all()  # Fetch all users from the database
    for user in users:
        print(f"Username: {user.username} | Password Hash: {user.password}")

if __name__ == "__main__":
    print_users_and_passwords()
