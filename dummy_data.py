import os
import django
from django.db import connection
import random

# Set up Django environment
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'pharmacy_management.settings')
django.setup()

# Import models
from django.contrib.auth.models import User
from django.core.management import call_command
from home.models import Manufacturer, Product, Category
from home.utils import log_activity

# Clear all data, reset auto-increment values
def reset_database():
    call_command('flush', '--no-input')  # Remove all data
    call_command('migrate')  # Reapply migrations

    with connection.cursor() as cursor:
        # Only update sequence for 'django_session' table (session_key column)
        cursor.execute("""
            SELECT c.relname, pg_get_serial_sequence(c.oid::regclass::text, 'session_key') 
            FROM pg_class c 
            JOIN pg_namespace n ON n.oid = c.relnamespace
            WHERE c.relkind = 'r' 
              AND n.nspname = 'public'
              AND c.relname = 'django_session'  -- Target only 'django_session' table
              AND pg_get_serial_sequence(c.oid::regclass::text, 'session_key') IS NOT NULL
        """)
        sequences = cursor.fetchall()

        for table_name, sequence_name in sequences:
            if sequence_name:  # Ensure the table actually has a sequence
                cursor.execute(f"ALTER SEQUENCE {sequence_name} RESTART WITH 1")

# Create users
def create_users():
    # Ensure admin user is created first
    admin_user = User.objects.create_superuser(username='admin', password='hsbochum!')
    admin_user.first_name = 'admin'
    admin_user.save()
    log_activity(
        admin_user, 
        action=f"added new user {admin_user.username}",
        additional_info=f"user ID: {admin_user.id}"
    )            

    # Create toan user
    toan_user = User.objects.create_user(username='toan', password='toan5987ng')
    toan_user.first_name = 'Toan'
    toan_user.is_staff = True  # Make the user a staff member
    toan_user.save()
    log_activity(
        admin_user,
        action=f"added new user {toan_user.username}",
        additional_info=f"user ID: {toan_user.id}"
    )

# Create manufacturers
def create_manufacturers():
    manufacturers_data = [
        {"name": "Pfizer", "address": "5 Giralda Farms, Madison, New Jersey, USA", "phone_number": "+1 800-879-3477", "email": "contact@pfizer.com"},
        {"name": "Johnson & Johnson", "address": "One Johnson & Johnson Plaza, New Brunswick, NJ 08933", "phone_number": "+1 800-962-5357", "email": "info@jnj.com"},
        {"name": "AstraZeneca", "address": "1 Francis Crick Avenue, Cambridge, UK", "phone_number": "+44 1223 343300", "email": "contact@astrazeneca.com"},
        {"name": "Novartis", "address": "Balerna, Switzerland", "phone_number": "+41 61 324 1111", "email": "info@novartis.com"},
    ]

    for manufacturer_data in manufacturers_data:
        manufacturer, created = Manufacturer.objects.get_or_create(
            name=manufacturer_data['name'],
            defaults=manufacturer_data
        )
        if created:
            log_activity(
                User.objects.get(username='admin'),
                action=f"added new manufacturer {manufacturer.name}",
                additional_info=f"manufacturer ID: {manufacturer.id}"
            )

# Create product categories
def create_product_categories():
    categories_data = [
        {"name": "Over The Counter", "description": "Products that do not require a prescription", "requires_prescription": False},
        {"name": "Pharmacy Only", "description": "Products available only at pharmacies", "requires_prescription": False},
        {"name": "Prescription Only", "description": "Products that require a doctor's prescription", "requires_prescription": True},
        {"name": "Controlled Substances", "description": "Products under strict regulation and require a prescription", "requires_prescription": True},
    ]

    for category_data in categories_data:
        category, created = Category.objects.get_or_create(
            name=category_data['name'],
            defaults={"description": category_data['description'], "requires_prescription": category_data['requires_prescription']}
        )
        if created:
            log_activity(
                User.objects.get(username='admin'),
                action=f"added new category {category.name}",
                additional_info=f"category ID: {category.id}"
            )

# Create products
def create_products(): 
    # Fetch product categories from the database
    categories = {category.name: category for category in Category.objects.all()}
    admin_user = User.objects.get(username='admin') # Fetch the admin username
    
    for manufacturer in Manufacturer.objects.all():
        # Over The Counter products
        for i in range(1, 4):
            sale_price = round(random.uniform(5.00, 15.00), 2)
            product, created = Product.objects.get_or_create(
                name=f"OTC Product {manufacturer.name} {i}",
                category=categories["Over The Counter"],
                manufacturer=manufacturer,
                sale_price=sale_price,
                defaults={"description": f"Over the Counter product by {manufacturer.name}"}
            )
            if created:
                log_activity(
                    admin_user,
                    action=f"added new product {product.name}",
                    additional_info=f"product ID: {product.id}, category: {product.category.name}, manufacturer: {manufacturer.name}"
                )

        # Pharmacy Only products
        for i in range(1, 4):
            sale_price = round(random.uniform(10.00, 20.00), 2)
            product, created = Product.objects.get_or_create(
                name=f"Pharmacy Only Product {manufacturer.name} {i}",
                category=categories["Pharmacy Only"],
                manufacturer=manufacturer,
                sale_price=sale_price,
                defaults={"description": f"Pharmacy Only product by {manufacturer.name}"}
            )
            if created:
                log_activity(
                    admin_user,
                    action=f"added new product {product.name}",
                    additional_info=f"product ID: {product.id}, category: {product.category.name}, manufacturer: {manufacturer.name}"
                )

        # Prescription Only products
        for i in range(1, 4):
            sale_price = round(random.uniform(30.00, 60.00), 2)
            product, created = Product.objects.get_or_create(
                name=f"Prescription Only Product {manufacturer.name} {i}",
                category=categories["Prescription Only"],
                manufacturer=manufacturer,
                sale_price=sale_price,
                defaults={"description": f"Prescription Only product by {manufacturer.name}"}
            )
            if created:
                log_activity(
                    admin_user,
                    action=f"added new product {product.name}",
                    additional_info=f"product ID: {product.id}, category: {product.category.name}, manufacturer: {manufacturer.name}"
                )

        # Controlled Substances product
        sale_price = round(random.uniform(80.00, 150.00), 2)
        product, created = Product.objects.get_or_create(
            name=f"Controlled Substance Product {manufacturer.name} 1",
            category=categories["Controlled Substances"],
            manufacturer=manufacturer,
            sale_price=sale_price,
            defaults={"description": f"Controlled Substance product by {manufacturer.name}"}
        )
        if created:
            log_activity(
                admin_user,
                action=f"added new product {product.name}",
                additional_info=f"product ID: {product.id}, category: {product.category.name}, manufacturer: {manufacturer.name}"
            )

# Main function
if __name__ == '__main__':
    # Clear all existing data
    reset_database()
    print("Database has been reset successfully!")

    # Create users
    create_users()
    print("Users have been created successfully!")

    # Create manufacturers
    create_manufacturers()
    print("Manufacturers have been created successfully!")

    # Create product categories
    create_product_categories()
    print("Product categories have been created successfully!")

    # Create products
    create_products()
    print("Products have been created successfully!")

    print("Dummy data has been created successfully!")
