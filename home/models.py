# home/models.py
from django.db import models
from django.contrib.auth.models import User
from django.utils import timezone
from django.utils.translation import gettext_lazy as _

from .validators import validate_phone_number  # Import the validator

# Activity Log
class ActivityLog(models.Model):
    timestamp = models.DateTimeField(_("Timestamp"), auto_now_add=True)  # Automatically record the time of the action
    user = models.ForeignKey(User, verbose_name=_("User"), on_delete=models.CASCADE)  # Reference to the user who performed the action
    action = models.CharField(_("Action"), max_length=255)  # Brief description of the action
    additional_info = models.TextField(_("Additional Info"), blank=True, null=True)  # Optional additional information

    class Meta:
        ordering = ['-timestamp']  # Sort by most recent logs by default
        verbose_name = _("Activity Log")
        verbose_name_plural = _("Activity Logs")

    def __str__(self):
        return f"{self.timestamp} - {self.user.username} - {self.action}"
    
# Manufacturer management    
class Manufacturer(models.Model):
    name = models.CharField(_("Name"), max_length=200, unique=True)  # Manufacturer's name
    address = models.TextField(_("Address"), blank=True, null=True)  # Address of the manufacturer
    phone_number = models.CharField(_("Phone Number"), max_length=20, blank=True, null=True, validators=[validate_phone_number])
    email = models.EmailField(_("Email"), blank=True, null=True)  # Contact email
    created_at = models.DateTimeField(_("Created At"), auto_now_add=True)  # Date of creation
    updated_at = models.DateTimeField(_("Updated At"), auto_now=True)  # Date of last update

    class Meta:
        ordering = ['-updated_at']
        verbose_name = _("Manufacturer")
        verbose_name_plural = _("Manufacturers")

    def __str__(self):
        return self.name

# Category management
class Category(models.Model):
    name = models.CharField(_("Name"), max_length=200, unique=True)  # Category name
    description = models.TextField(_("Description"), blank=True, null=True)  # Category description
    requires_prescription = models.BooleanField(_("Requires Prescription"), default=False)  # Checkbox to indicate if prescription is required
    low_stock_threshold = models.PositiveIntegerField(_("Low Stock Threshold"), default=10)  # Threshold for low stock alert
    created_at = models.DateTimeField(_("Created At"), auto_now_add=True)  # Date of creation
    updated_at = models.DateTimeField(_("Updated At"), auto_now=True)  # Date of last update

    class Meta:
        ordering = ['-updated_at']
        verbose_name = _("Category")
        verbose_name_plural = _("Categories")

    def __str__(self):
        return self.name

# Product management
class Product(models.Model):    
    name = models.CharField(_("Name"), max_length=200)  # Product name
    category = models.ForeignKey(Category, verbose_name=_("Category"), on_delete=models.PROTECT)  # Linking to the Category model
    manufacturer = models.ForeignKey(Manufacturer, verbose_name=_("Manufacturer"), on_delete=models.PROTECT, db_index=True)  # Manufacturer of the product
    sale_price = models.DecimalField(_("Sale Price"), max_digits=10, decimal_places=2)  # Sale price
    description = models.TextField(_("Description"), blank=True, null=True)  # Product description
    created_at = models.DateTimeField(_("Created At"), auto_now_add=True)  # Date of creation
    updated_at = models.DateTimeField(_("Updated At"), auto_now=True)  # Date of last update

    class Meta:
        ordering = ['-updated_at']
        verbose_name = _("Product")
        verbose_name_plural = _("Products")

    def __str__(self):
        return self.name

# Inventory management    
class Inventory(models.Model):
    product = models.ForeignKey(Product, verbose_name=_("Product"), on_delete=models.PROTECT, related_name='inventory', db_index=True)  # Reference to the product
    quantity = models.PositiveIntegerField(_("Quantity"))  # Quantity in stock
    expiry_date = models.DateField(_("Expiry Date"))  # Expiry date of the product
    created_at = models.DateTimeField(_("Created At"), auto_now_add=True)  # Date of creation
    updated_at = models.DateTimeField(_("Updated At"), auto_now=True)  # Date of last update

    class Meta:
        ordering = ['-updated_at']
        constraints = [
            models.UniqueConstraint(fields=['product', 'expiry_date'], name='unique_product_expiry')
        ]
        verbose_name = _("Inventory")
        verbose_name_plural = _("Inventories")

    def __str__(self):
        return f"{self.product.name} - {self.quantity} units - Expires on {self.expiry_date}"

# Purchase Transaction management
class PurchaseTransaction(models.Model):
    manufacturer = models.ForeignKey(Manufacturer, verbose_name=_("Manufacturer"), on_delete=models.PROTECT, db_index=True)  # Manufacturer from whom products are purchased
    purchase_date = models.DateTimeField(_("Purchase Date"), default=timezone.now)
    invoice_number = models.CharField(_("Invoice Number"), max_length=100, unique=True)  # Unique invoice or bill number
    total_cost = models.DecimalField(_("Total Cost"), max_digits=15, decimal_places=2)  # Total cost of the purchase
    remarks = models.TextField(_("Remarks"), blank=True, null=True)  # Additional remarks or notes about the transaction
    created_by = models.ForeignKey(User, verbose_name=_("Created By"), on_delete=models.SET_NULL, null=True, blank=True)
    created_at = models.DateTimeField(_("Created At"), auto_now_add=True)  # Date of creation

    class Meta:
        ordering = ['-created_at']
        verbose_name = _("Purchase Transaction")
        verbose_name_plural = _("Purchase Transactions")

    def __str__(self):
        return f"Invoice #{self.invoice_number} - {self.manufacturer.name if self.manufacturer else 'N/A'} - {self.purchase_date}"

    # Add total_cost property to calculate the total cost of all products in a transaction
    @property
    def total_cost_computed(self):
        return sum(p.total_price for p in self.purchased_products.all())

class PurchasedProduct(models.Model):
    purchase_transaction = models.ForeignKey(PurchaseTransaction, verbose_name=_("Purchase Transaction"), on_delete=models.CASCADE, related_name='purchased_products')  # Reference to the purchase transaction
    product = models.ForeignKey(Product, verbose_name=_("Product"), on_delete=models.PROTECT, db_index=True)  # Product being purchased
    batch_number = models.CharField(_("Batch Number"), max_length=100, blank=True, null=True)  # Batch or lot number for tracking
    quantity = models.PositiveIntegerField(_("Quantity"))  # Quantity purchased
    purchase_price = models.DecimalField(_("Purchase Price"), max_digits=10, decimal_places=2)  # Purchase price
    expiry_date = models.DateField(_("Expiry Date"))  # Expiry date of the product

    class Meta:
        ordering = ['-expiry_date']
        verbose_name = _("Purchased Product")
        verbose_name_plural = _("Purchased Products")

    @property
    def total_price(self):
        return self.quantity * self.purchase_price  # Total price for this product

    def __str__(self):
        return f"{self.product.name} - {self.quantity} units @ {self.purchase_price}€"

# Customer management
class Customer(models.Model):
    full_name = models.CharField(_("Full Name"), max_length=200)
    birthdate = models.DateField(_("Birthdate"), blank=True, null=True)
    phone_number = models.CharField(_("Phone Number"), max_length=20, blank=True, null=True, validators=[validate_phone_number])
    email = models.EmailField(_("Email"), blank=True, null=True)
    address = models.TextField(_("Address"), blank=True, null=True)
    created_at = models.DateTimeField(_("Created At"), auto_now_add=True)
    updated_at = models.DateTimeField(_("Updated At"), auto_now=True)

    class Meta:
        ordering = ['-updated_at']
        verbose_name = _("Customer")
        verbose_name_plural = _("Customers")

    def __str__(self):
        return self.full_name

# Sale Transaction management
class SaleTransaction(models.Model):
    transaction_number = models.CharField(_("Transaction Number"), max_length=100, unique=True)
    customer = models.ForeignKey(Customer, verbose_name=_("Customer"), on_delete=models.SET_NULL, null=True, blank=True, db_index=True)
    transaction_date = models.DateTimeField(_("Transaction Date"), default=timezone.now)
    
    # Prices and payments
    price = models.DecimalField(_("Price"), max_digits=15, decimal_places=2, default=0.00)  # Total before discount
    discount = models.DecimalField(_("Discount"), max_digits=10, decimal_places=2, default=0.00, blank=True)
    total = models.DecimalField(_("Total"), max_digits=15, decimal_places=2, default=0.00)  # Final total = price - discount
    cash_received = models.DecimalField(_("Cash Received"), max_digits=15, decimal_places=2, default=0.00, blank=True)

    @property
    def total_amount(self):
        return sum(item.total_price for item in self.sold_products.all())

    payment_method = models.CharField(
        _("Payment Method"),
        max_length=20,
        choices=[
            ('Cash', _("Cash")),
            ('Card', _("Card")),
            ('Insurance', _("Insurance"))
        ],
        default='Cash'
    )
    
    remarks = models.TextField(_("Remarks"), blank=True, null=True)
    created_by = models.ForeignKey(User, verbose_name=_("Created By"), on_delete=models.SET_NULL, null=True, blank=True)
    created_at = models.DateTimeField(_("Created At"), auto_now_add=True)

    class Meta:
        ordering = ['-created_at']
        verbose_name = _("Sale Transaction")
        verbose_name_plural = _("Sale Transactions")

    def __str__(self):
        return f"Transaction #{self.transaction_number}"

    @property
    def to_be_paid(self):
        return max(self.price - self.discount, 0)

    @property
    def change(self):
        return max(self.cash_received - self.to_be_paid, 0)

class SoldProduct(models.Model):
    sale_transaction = models.ForeignKey(SaleTransaction, verbose_name=_("Sale Transaction"), on_delete=models.CASCADE, related_name='sold_products')
    inventory_item = models.ForeignKey(Inventory, verbose_name=_("Inventory Item"), on_delete=models.PROTECT)
    quantity = models.PositiveIntegerField(_("Quantity"))
    sale_price = models.DecimalField(_("Sale Price"), max_digits=10, decimal_places=2)

    class Meta:
        ordering = ['-inventory_item__expiry_date']
        verbose_name = _("Sold Product")
        verbose_name_plural = _("Sold Products")

    @property
    def total_price(self):
        return self.quantity * self.sale_price

    def __str__(self):
        return f"{self.inventory_item.product.name} - {self.quantity} units @ {self.sale_price}€"

# Discount management
class Discount(models.Model):
    name = models.CharField(_("Name"), max_length=100)
    products = models.ManyToManyField(Product, verbose_name=_("Products"), related_name='discounts')
    percentage = models.DecimalField(_("Percentage"), max_digits=5, decimal_places=2, help_text=_("Enter percentage, e.g. 10.00 for 10%"))
    from_date = models.DateField(_("From Date"))
    to_date = models.DateField(_("To Date"))

    class Meta:
        verbose_name = _("Discount")
        verbose_name_plural = _("Discounts")

    def __str__(self):
        return f"{self.name} ({self.percentage}% from {self.from_date} to {self.to_date})"

    def is_active(self, date=None):
        date = date or timezone.now().date()
        return self.from_date <= date <= self.to_date
