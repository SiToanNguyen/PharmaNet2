# count_transactions.py

import os
import django

# Setup Django environment
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'pharmacy_management.settings')
django.setup()

from home.models import Manufacturer, Customer, PurchaseTransaction, SaleTransaction

def count_transactions():
    manufacturer_count = Manufacturer.objects.count()
    customer_count = Customer.objects.count()
    purchase_count = PurchaseTransaction.objects.count()
    sale_count = SaleTransaction.objects.count()

    print(f"Total Manufacturers: {manufacturer_count}")
    print(f"Total Customers: {customer_count}")
    print(f"Total Purchase Transactions: {purchase_count}")
    print(f"Total Sale Transactions: {sale_count}")

if __name__ == "__main__":
    count_transactions()
