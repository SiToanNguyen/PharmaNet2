import os
import django

# Set up Django environment
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "pharmacy_management.settings")
django.setup()

from home.models import Manufacturer, Product 

def list_manufacturers_and_products():
    manufacturers = Manufacturer.objects.all()

    if not manufacturers.exists():
        print("No manufacturers found.")
        return

    for manufacturer in manufacturers:
        print(f"Manufacturer: {manufacturer.name}")
        products = Product.objects.filter(manufacturer=manufacturer)
        if products.exists():
            for product in products:
                print(f"  - Product: {product.name}")
        else:
            print("  (No products)")
        print()

if __name__ == "__main__":
    list_manufacturers_and_products()
