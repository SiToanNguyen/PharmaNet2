# home/forms.py
from django import forms
from django.contrib.auth.models import User
from django.core.exceptions import ValidationError
from django.utils import timezone
from .models import Manufacturer, Category, Product, Inventory, PurchaseTransaction, PurchasedProduct, Customer, SaleTransaction, SoldProduct
import re  # Import the re module for regex validation

# User management
class UserCreationForm(forms.ModelForm):
    password = forms.CharField(
        widget=forms.PasswordInput,
        help_text="Password cannot consist only of spaces.",
    )
    is_active = forms.BooleanField(initial=True, required=False)  # Ensure is_active is True by default

    class Meta:
        model = User
        fields = ['username', 'password', 'email', 'first_name', 'last_name', 'is_staff', 'is_superuser', 'is_active']
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['is_active'].initial = True  # Set 'is_active' to True by default

    def clean_password(self):
        password = self.cleaned_data.get('password', '').strip()
        if not password:
            raise ValidationError("Password cannot consist only of spaces.")
        return password
    
    # Override save to handle password hashing correctly
    def save(self, commit=True):
        user = super().save(commit=False)
        user.set_password(self.cleaned_data["password"])
        if commit:
            user.save()
        return user

class UserEditForm(forms.ModelForm):
    password = forms.CharField(
        widget=forms.PasswordInput, 
        required=False, 
        help_text="Leave empty to keep the current password."
    )
    
    class Meta:
        model = User
        fields = ['username', 'password', 'email', 'first_name', 'last_name', 'is_staff', 'is_superuser', 'is_active']

    def save(self, commit=True):
        user = super().save(commit=False)
        password = self.cleaned_data.get('password', '')  # Get password

        # Only set a new password if one is provided
        if password:
            user.set_password(password)

        if commit:
            user.save()
        return user

# Manufacturer management
class ManufacturerForm(forms.ModelForm):
    class Meta:
        model = Manufacturer
        fields = ['name', 'address', 'phone_number', 'email']

    def clean_name(self):
        name = self.cleaned_data.get('name')
        if Manufacturer.objects.filter(name=name).exists():
            raise forms.ValidationError("A manufacturer with this name already exists. Please choose another name.")
        return name

    # Validate the phone number format
    def clean_phone_number(self):
        phone_number = self.cleaned_data.get('phone_number')
        # Example validation: check the phone number pattern
        if not re.match(r'^\+?\d{1,4}?[-.\s]?\(?\d{1,4}?\)?[-.\s]?\d{1,9}[-.\s]?\d{1,9}$', phone_number):
            raise forms.ValidationError('Enter a valid phone number (e.g., +1-800-123-4567).')
        return phone_number

# Category management
class CategoryForm(forms.ModelForm):
    class Meta:
        model = Category
        fields = ['name', 'description', 'requires_prescription']

    def clean_name(self):
        name = self.cleaned_data.get('name')
        if Category.objects.filter(name=name).exists():
            raise forms.ValidationError("A category with this name already exists. Please choose another name.")
        return name

# Product management
class ProductForm(forms.ModelForm):
    class Meta:
        model = Product
        fields = ['name', 'category', 'manufacturer', 'sale_price', 'description']

    def clean_name(self):
        name = self.cleaned_data.get('name')
        if Product.objects.filter(name=name).exists():
            raise forms.ValidationError("A product with this name already exists. Please choose another name.")
        return name

# Purchase Transaction management
class PurchaseTransactionForm(forms.ModelForm):
    purchase_date = forms.DateField(
        widget=forms.DateInput(attrs={'type': 'date'}),
        required=True
    )  # Use <input type="date"> for selecting purchase date

    total_cost = forms.DecimalField(
        max_digits=15, decimal_places=2, required=False, widget=forms.NumberInput(attrs={'readonly': 'readonly'})
    )  # Total cost is read-only

    remarks = forms.CharField(
        widget=forms.Textarea(attrs={'rows': 3}),
        required=False
    )  # Remarks field

    class Meta:
        model = PurchaseTransaction
        fields = ['invoice_number', 'manufacturer', 'purchase_date', 'remarks', 'total_cost']

    def clean_invoice_number(self):
        invoice_number = self.cleaned_data.get('invoice_number')
        if PurchaseTransaction.objects.filter(invoice_number=invoice_number).exists():
            raise ValidationError("A purchase transaction with this invoice number already exists.")
        return invoice_number
    
    def clean_purchase_date(self):
        purchase_date = self.cleaned_data.get('purchase_date')
        if purchase_date:
            # Ensure the date is timezone-aware
            return timezone.make_aware(timezone.datetime.combine(purchase_date, timezone.datetime.min.time()))
        return purchase_date
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

class PurchasedProductForm(forms.ModelForm):
    batch_number = forms.CharField(required=False)  # Batch number is optional
    quantity = forms.IntegerField(min_value=1, required=True)  # Quantity should be at least 1
    expiry_date = forms.DateField(widget=forms.DateInput(attrs={'type': 'date'}), required=True)  # Expiry date field
    purchase_price = forms.DecimalField(
        max_digits=10,
        decimal_places=2,
        min_value=0.01,  # Ensure purchase price is greater than zero
        required=True
    )

    class Meta:
        model = PurchasedProduct
        fields = ['product', 'batch_number', 'quantity', 'purchase_price', 'expiry_date']

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Initially allow all products; the view will override this if needed
        self.fields['product'].queryset = Product.objects.all()

    def clean_purchase_price(self):
        purchase_price = self.cleaned_data.get('purchase_price')
        if purchase_price <= 0:
            raise forms.ValidationError("Purchase price must be greater than zero.")
        return purchase_price

# Customer management
class CustomerForm(forms.ModelForm):
    birthdate = forms.DateField(
        widget=forms.DateInput(attrs={'type': 'date'}),
        required=True
    ) # Use <input type="date"> for selecting birthdate

    class Meta:
        model = Customer
        fields = ['full_name', 'birthdate', 'phone_number', 'email', 'address']

# Sale Transaction management
class SaleTransactionForm(forms.ModelForm):
    class Meta:
        model = SaleTransaction
        fields = [
            'transaction_number',
            'customer',
            'discount',
            'cash_received',
            'payment_method',
            'remarks'
        ]
        widgets = {
            'transaction_number': forms.TextInput(attrs={'placeholder': 'Enter transaction number'}),
            'discount': forms.NumberInput(attrs={'step': '1'}),
            'cash_received': forms.NumberInput(attrs={'step': '1'}),
            'remarks': forms.Textarea(attrs={'rows': 2}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['discount'].initial = '0'
        self.fields['cash_received'].initial = '0'

class SoldProductForm(forms.ModelForm):
    class Meta:
        model = SoldProduct
        fields = [
            'inventory_item',
            'quantity'
        ]
        widgets = {
            'quantity': forms.NumberInput(attrs={'min': 1})
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['inventory_item'].queryset = Inventory.objects.filter(quantity__gt=0)
        self.fields['inventory_item'].label_from_instance = lambda obj: f"{obj.product.name} (Exp: {obj.expiry_date}) — {obj.quantity} left"

class DateRangeForm(forms.Form):
    from_date = forms.DateField(widget=forms.DateInput(attrs={'type': 'date'}))
    to_date = forms.DateField(widget=forms.DateInput(attrs={'type': 'date'}))