# dummy_data.py
import os
import django
import random

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'pharmacy_management.settings')
django.setup()

from django.contrib.auth.models import User
from django.core.management import call_command
from home.models import Manufacturer, Product, Category
from home.utils import log_activity

from dummy_transaction import create_purchase_transactions, create_sale_transactions

from faker import Faker

fake = Faker()

def reset_database():
    call_command('flush', '--no-input')
    call_command('migrate')

def create_users():
    admin = User.objects.create_superuser(username='admin', password='hsbochum!')
    admin.first_name = 'Admin'
    admin.save()
    log_activity(admin, "added new user admin", "Superuser account")

    staff = User.objects.create_user(username='toan', password='toan5987ng', is_staff=True)
    staff.first_name = 'Toan'
    staff.save()
    log_activity(admin, "added new user toan", "Staff account")

def create_categories():
    data = [
        ("Over The Counter", "Products that do not require a prescription", False),
        ("Pharmacy Only", "Products available only at pharmacies", False),
        ("Prescription Only", "Products that require a doctor's prescription", True),
        ("Controlled Substances", "Strictly regulated products", True)
    ]
    for name, desc, required in data:
        cat, created = Category.objects.get_or_create(name=name, defaults={"description": desc, "requires_prescription": required})
        if created:
            log_activity(User.objects.get(username="admin"), f"added new category {name}", f"Prescription: {required}")

def create_manufacturers():
    admin = User.objects.get(username="admin")
    for _ in range(10):
        name = fake.company()
        address = fake.address().replace('\n', ', ')
        phone = fake.phone_number()[:20]
        email = fake.company_email()

        manufacturer = Manufacturer.objects.create(
            name=name,
            address=address,
            phone_number=phone,
            email=email
        )

        log_activity(admin, f"added new manufacturer {name}", f"ID: {manufacturer.id}")

def create_products():
    admin = User.objects.get(username="admin")
    categories = {cat.name: cat for cat in Category.objects.all()}
    price_ends = [".99", ".49"]

    for manu in Manufacturer.objects.all():
        # Controlled Substances (1)
        create_random_product(manu, categories["Controlled Substances"], 1, 100, 150, price_ends, admin)

        # Prescription Only (2)
        create_random_product(manu, categories["Prescription Only"], 2, 40, 80, price_ends, admin)

        # Pharmacy Only (3)
        create_random_product(manu, categories["Pharmacy Only"], 3, 20, 40, price_ends, admin)

        # Over The Counter (4)
        create_random_product(manu, categories["Over The Counter"], 4, 5, 20, price_ends, admin)

def create_random_product(manu, category, count, price_min, price_max, suffixes, user):
    for i in range(count):
        suffix = random.choice(suffixes)
        price = float(f"{random.randint(price_min, price_max)}{suffix}")
        name = f"{category.name} {manu.name} {i+1}"
        product = Product.objects.create(
            name=name,
            category=category,
            manufacturer=manu,
            sale_price=price,
            description=f"{category.name} product"
        )
        log_activity(user, f"added new product {name}", f"Category: {category.name}, Price: {price:.2f}")

if __name__ == '__main__':
    reset_database()
    create_users()
    create_categories()
    create_manufacturers()
    create_products()
    print("Dummy data successfully generated.")

    create_purchase_transactions()
    create_sale_transactions()
