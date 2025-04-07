# Create or reset the admin user
import os
import django

# Set the environment variable to your Django settings module
os.environ['DJANGO_SETTINGS_MODULE'] = 'pharmacy_management.settings'

# Set up Django
django.setup()

from django.contrib.auth.models import User

def create_admin_user():
    try:
        # Check if the admin user exists
        admin_user = User.objects.filter(username='admin').first()

        if admin_user:
            # If admin user exists, delete it
            admin_user.delete()
            print("Existing admin user 'admin' deleted.")

        # Create a new admin user
        admin_user = User.objects.create_superuser(username='admin', password='hsbochum!')
        admin_user.first_name = 'admin'
        admin_user.save()
        print("Admin user 'admin' created successfully with superuser privileges.")

    except Exception as e:
        print(f"Error creating admin user: {e}")

if __name__ == "__main__":
    create_admin_user()
