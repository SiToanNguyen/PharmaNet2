# home/models.py
from django.db import models
from django.contrib.auth.models import User
from django.utils import timezone

from .validators import validate_phone_number  # Import the validator

# Activity Log
class ActivityLog(models.Model):
    timestamp = models.DateTimeField(auto_now_add=True)  # Automatically record the time of the action
    user = models.ForeignKey(User, on_delete=models.CASCADE)  # Reference to the user who performed the action
    action = models.CharField(max_length=255)  # Brief description of the action
    additional_info = models.TextField(blank=True, null=True)  # Optional additional information

    class Meta:
        ordering = ['-timestamp']  # Sort by most recent logs by default

    def __str__(self):
        return f"{self.timestamp} - {self.user.username} - {self.action}"
    
# Manufacturer management    
class Manufacturer(models.Model):
    name = models.CharField(max_length=200, unique=True)  # Manufacturer's name
    address = models.TextField(blank=True, null=True)  # Address of the manufacturer
    phone_number = models.CharField(max_length=20, blank=True, null=True, validators=[validate_phone_number])
    email = models.EmailField(blank=True, null=True)  # Contact email
    created_at = models.DateTimeField(auto_now_add=True)  # Date of creation
    updated_at = models.DateTimeField(auto_now=True)  # Date of last update

    class Meta:
        ordering = ['-updated_at']

    def __str__(self):
        return self.name

# Category management
class Category(models.Model):
    name = models.CharField(max_length=200)  # Category name
    description = models.TextField(blank=True, null=True)  # Category description
    requires_prescription = models.BooleanField(default=False)  # Checkbox to indicate if prescription is required
    low_stock_threshold = models.PositiveIntegerField(default=10)  # Threshold for low stock alert
    created_at = models.DateTimeField(auto_now_add=True)  # Date of creation
    updated_at = models.DateTimeField(auto_now=True)  # Date of last update

    class Meta:
        ordering = ['-updated_at']

    def __str__(self):
        return self.name

# Product management
class Product(models.Model):    
    name = models.CharField(max_length=200)  # Product name
    category = models.ForeignKey(Category, on_delete=models.PROTECT)  # Linking to the Category model
    manufacturer = models.ForeignKey(Manufacturer, on_delete=models.PROTECT)  # Manufacturer of the product
    sale_price = models.DecimalField(max_digits=10, decimal_places=2)  # Sale price
    description = models.TextField(blank=True, null=True)  # Product description
    created_at = models.DateTimeField(auto_now_add=True)  # Date of creation
    updated_at = models.DateTimeField(auto_now=True)  # Date of last update

    class Meta:
        ordering = ['-updated_at']

    def __str__(self):
        return self.name

# Inventory management    
class Inventory(models.Model):
    product = models.ForeignKey(Product, on_delete=models.PROTECT, related_name='inventory')  # Reference to the product
    quantity = models.PositiveIntegerField()  # Quantity in stock
    expiry_date = models.DateField()  # Expiry date of the product
    created_at = models.DateTimeField(auto_now_add=True)  # Date of creation
    updated_at = models.DateTimeField(auto_now=True)  # Date of last update

    class Meta:
        ordering = ['-updated_at']
        constraints = [
            models.UniqueConstraint(fields=['product', 'expiry_date'], name='unique_product_expiry')
        ]

    def __str__(self):
        return f"{self.product.name} - {self.quantity} units - Expires on {self.expiry_date}"

# Purchase Transaction management
class PurchaseTransaction(models.Model):
    manufacturer = models.ForeignKey(Manufacturer, on_delete=models.PROTECT)  # Manufacturer from whom products are purchased
    purchase_date = models.DateTimeField(default=timezone.now)
    invoice_number = models.CharField(max_length=100, unique=True)  # Unique invoice or bill number
    total_cost = models.DecimalField(max_digits=15, decimal_places=2)  # Total cost of the purchase
    remarks = models.TextField(blank=True, null=True)  # Additional remarks or notes about the transaction
    created_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)  # Date of creation

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"Invoice #{self.invoice_number} - {self.manufacturer.name} - {self.purchase_date}"

class PurchasedProduct(models.Model):
    purchase_transaction = models.ForeignKey(PurchaseTransaction, on_delete=models.CASCADE, related_name='purchased_products')  # Reference to the purchase transaction
    product = models.ForeignKey(Product, on_delete=models.PROTECT)  # Product being purchased
    batch_number = models.CharField(max_length=100, blank=True, null=True)  # Batch or lot number for tracking
    quantity = models.PositiveIntegerField()  # Quantity purchased
    purchase_price = models.DecimalField(max_digits=10, decimal_places=2)  # Purchase price
    expiry_date = models.DateField()  # Expiry date of the product

    class Meta:
        ordering = ['-expiry_date']

    @property
    def total_price(self):
        return self.quantity * self.purchase_price  # Total price for this product

    def __str__(self):
        return f"{self.product.name} - {self.quantity} units @ {self.purchase_price}€"

    # Add total_cost property to calculate the total cost of all products in a transaction
    @property
    def calculate_total_cost(self):
        return sum([p.total_price for p in self.purchased_products.all()])

# Customer management
class Customer(models.Model):
    full_name = models.CharField(max_length=200)
    birthdate = models.DateField(blank=True, null=True)
    phone_number = models.CharField(max_length=20, blank=True, null=True, validators=[validate_phone_number])
    email = models.EmailField(blank=True, null=True)
    address = models.TextField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-updated_at']

    def __str__(self):
        return self.full_name

# Sale Transaction management
class SaleTransaction(models.Model):
    transaction_number = models.CharField(max_length=100, unique=True)
    customer = models.ForeignKey('Customer', on_delete=models.SET_NULL, null=True, blank=True)
    transaction_date = models.DateTimeField(default=timezone.now)
    
    # Prices and payments
    price = models.DecimalField(max_digits=15, decimal_places=2, default=0.00)  # Total before discount
    discount = models.DecimalField(max_digits=10, decimal_places=2, default=0.00, blank=True)
    total = models.DecimalField(max_digits=15, decimal_places=2, default=0.00)  # Final total = price - discount
    cash_received = models.DecimalField(max_digits=15, decimal_places=2, default=0.00, blank=True)

    @property
    def total_amount(self):
        return sum([item.total_price for item in self.sold_products.all()])

    payment_method = models.CharField(
        max_length=20,
        choices=[('Cash', 'Cash'), ('Card', 'Card'), ('Insurance', 'Insurance')],
        default='Cash'
    )
    
    remarks = models.TextField(blank=True, null=True)
    created_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"Transaction #{self.transaction_number}"

    @property
    def to_be_paid(self):
        return max(self.price - self.discount, 0)

    @property
    def change(self):
        return max(self.cash_received - self.to_be_paid, 0)

class SoldProduct(models.Model):
    sale_transaction = models.ForeignKey(SaleTransaction, on_delete=models.CASCADE, related_name='sold_products')
    inventory_item = models.ForeignKey(Inventory, on_delete=models.PROTECT)
    quantity = models.PositiveIntegerField()
    sale_price = models.DecimalField(max_digits=10, decimal_places=2)

    class Meta:
        ordering = ['-inventory_item__expiry_date']

    @property
    def total_price(self):
        return self.quantity * self.sale_price

    def __str__(self):
        return f"{self.inventory_item.product.name} - {self.quantity} units @ {self.sale_price}€"

# Discount management
class Discount(models.Model):
    name = models.CharField(max_length=100)
    products = models.ManyToManyField(Product, related_name='discounts')
    percentage = models.DecimalField(max_digits=5, decimal_places=2, help_text="Enter percentage, e.g. 10.00 for 10%")
    from_date = models.DateField()
    to_date = models.DateField()

    def __str__(self):
        return f"{self.name} ({self.percentage}% from {self.from_date} to {self.to_date})"

    def is_active(self, date=None):
        date = date or timezone.now().date()
        return self.from_date <= date <= self.to_date
