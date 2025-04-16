# dummy_transaction.py
import os
import django
import random
from datetime import timedelta
from django.utils.timezone import now
from decimal import Decimal
from uuid import uuid4
from datetime import datetime, timedelta
from faker import Faker

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'pharmacy_management.settings')
django.setup()

from home.models import *
from home.utils import log_activity

fake = Faker()

P = 2  # Purchase transactions per manufacturer
S = 200  # Total sale transactions

def get_random_date_within_range(start_date, end_date):
    """Returns a random timezone-aware datetime between start_date and end_date."""
    delta_days = (end_date - start_date).days
    random_days = random.randint(0, delta_days)
    random_date = start_date + timedelta(days=random_days)
    # Return timezone-aware datetime at midnight
    return timezone.make_aware(datetime.combine(random_date, datetime.min.time()))

def create_purchase_transactions():
    admin = User.objects.get(username="admin")
    today = now().date()
    four_years_ago = today - timedelta(days=4*365)

    for manu in Manufacturer.objects.all():
        products = Product.objects.filter(manufacturer=manu)
        for i in range(P):
            invoice = f"INV-{manu.id}-{i+1}-{uuid4().hex[:6]}"
            purchase_date = get_random_date_within_range(four_years_ago, today)  # Random date between 4 years ago and today
            tx = PurchaseTransaction.objects.create(
                manufacturer=manu,
                invoice_number=invoice,
                purchase_date=purchase_date,
                total_cost=0
            )
            for prod in products:
                quantity = random.randint(10, 50)
                price = round(random.uniform(1, float(prod.sale_price)), 2)
                expiry_offset = random.randint(-30, 1461)  # -30 days to +4 years
                expiry = today + timedelta(days=expiry_offset)

                item = PurchasedProduct.objects.create(
                    purchase_transaction=tx,
                    product=prod,
                    quantity=quantity,
                    purchase_price=price,
                    expiry_date=expiry
                )
                tx.total_cost += item.total_price

                inv, created = Inventory.objects.get_or_create(
                    product=prod,
                    expiry_date=expiry,
                    defaults={"quantity": quantity}
                )
                if not created:
                    inv.quantity += quantity
                    inv.save()

            tx.save()
            log_activity(admin, "added purchase transaction", f"{invoice} - {manu.name}")

def create_sale_transactions():
    admin = User.objects.get(username="admin")
    customers = list(Customer.objects.all())
    today = now().date()
    four_years_ago = today - timedelta(days=4*365)

    for i in range(S):
        # 1/3 no customer, 1/3 new, 1/3 existing
        choice = random.choice(["none", "new", "existing"])
        if choice == "none":
            customer = None
        elif choice == "new":
            customer = Customer.objects.create(
                full_name=fake.name(),
                birthdate=fake.date_of_birth(minimum_age=18, maximum_age=90),
                phone_number=fake.phone_number()[:20],
                address=fake.address().replace('\n', ', ')
            )
        else:
            if not customers:
                continue
            customer = random.choice(customers)

        transaction_date = get_random_date_within_range(four_years_ago, today)  # Random date between 4 years ago and today
        tx = SaleTransaction.objects.create(
            transaction_number=f"TX-{i+1}-{uuid4().hex[:6]}",
            customer=customer,
            created_by=admin,
            price=0,
            discount=random.choice([Decimal('0.00'), Decimal('2.50'), Decimal('5.00')]),
            cash_received=0,  # filled after
            payment_method=random.choice(["CASH", "CARD", "INSURANCE"]),
            transaction_date=transaction_date  # Setting the random date here
        )

        available_items = list(Inventory.objects.filter(quantity__gte=1))
        random.shuffle(available_items)

        for inv in available_items[:random.randint(1, 3)]:
            qty = random.randint(1, min(inv.quantity, 5))
            sale_price = inv.product.sale_price
            item = SoldProduct.objects.create(
                sale_transaction=tx,
                inventory_item=inv,
                quantity=qty,
                sale_price=sale_price
            )
            inv.quantity -= qty
            inv.save()
            tx.price += item.total_price
            
        tx.cash_received = tx.to_be_paid + Decimal(str(round(random.uniform(0, 5), 2)))
        tx.save()

        log_activity(admin, "added sale transaction", f"{tx.transaction_number} - Customer: {customer or 'N/A'}")

def generate_dummy_transaction():
    create_purchase_transactions()
    create_sale_transactions()
    print("Dummy purchase and sale transactions created.")

if __name__ == '__main__':
    generate_dummy_transaction()
