# home/forms.py
from django import forms
from django.contrib.auth.models import User
from django.core.exceptions import ValidationError
from django.utils import timezone
from .models import (
    Manufacturer, Category, Product, Inventory, PurchaseTransaction, PurchasedProduct, 
    Customer, SaleTransaction, SoldProduct, Discount)
from .validators import validate_phone_number

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
        qs = Manufacturer.objects.filter(name=name)
        if self.instance.pk:
            qs = qs.exclude(pk=self.instance.pk)
        if qs.exists():
            raise forms.ValidationError("A manufacturer with this name already exists. Please choose another name.")
        return name

    # Validate the phone number format
    def clean_phone_number(self):
        phone_number = self.cleaned_data.get('phone_number')
        validate_phone_number(phone_number)
        return phone_number

# Category management
class CategoryForm(forms.ModelForm):
    class Meta:
        model = Category
        fields = ['name', 'description', 'requires_prescription', 'low_stock_threshold']

    def clean_name(self):
        name = self.cleaned_data.get('name')
        # Exclude the current instance when editing
        qs = Category.objects.filter(name=name)
        if self.instance.pk:
            qs = qs.exclude(pk=self.instance.pk)
        if qs.exists():
            raise forms.ValidationError("A category with this name already exists. Please choose another name.")
        return name

# Product management
class ProductForm(forms.ModelForm):
    class Meta:
        model = Product
        fields = ['name', 'category', 'manufacturer', 'sale_price', 'description']

    def clean_name(self):
        name = self.cleaned_data.get('name')
        qs = Product.objects.filter(name=name)
        if self.instance.pk:
            qs = qs.exclude(pk=self.instance.pk)
        if qs.exists():
            raise forms.ValidationError("A product with this name already exists. Please choose another name.")
        return name

# Purchase Transaction management
class PurchaseTransactionForm(forms.ModelForm):
    class Meta:
        model = PurchaseTransaction
        exclude = ['total_cost'] # Exclude total_cost as it will be calculated automatically
        fields = [
            'invoice_number', 
            'manufacturer', 
            'purchase_date', 
            'remarks', 
            'total_cost'
        ]
        widgets = {
            'manufacturer': forms.Select(attrs={'class': 'form-control'}),
            'purchase_date': forms.DateInput(
                attrs={'type': 'date'},
                format='%Y-%m-%d'
            ),
            'remarks': forms.Textarea(attrs={'rows': 3}),
            'total_cost': forms.NumberInput(attrs={'readonly': 'readonly'})        
        }

    def clean_invoice_number(self):
        invoice_number = self.cleaned_data.get('invoice_number')
        qs = PurchaseTransaction.objects.filter(invoice_number=invoice_number)
        if self.instance.pk:
            qs = qs.exclude(pk=self.instance.pk)
        if qs.exists():
            raise forms.ValidationError("A purchase transaction with this invoice number already exists.")
        return invoice_number
    
    def clean_purchase_date(self):
        purchase_date = self.cleaned_data.get('purchase_date')
        if purchase_date:
            # Ensure the date is timezone-aware
            return timezone.make_aware(timezone.datetime.combine(purchase_date, timezone.datetime.min.time()))
        return purchase_date
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['purchase_date'].input_formats = ['%Y-%m-%d']
        if not self.instance.pk:
            self.fields['purchase_date'].initial = timezone.now()

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
        self.fields['product'].queryset = Product.objects.none()  # Start with empty list

    def clean_purchase_price(self):
        purchase_price = self.cleaned_data.get('purchase_price')
        if purchase_price <= 0:
            raise forms.ValidationError("Purchase price must be greater than zero.")
        return purchase_price

class PurchaseScanForm(forms.Form):
    json_file = forms.FileField(label="Scan Purchase JSON File", required=True)

# Customer management
class CustomerForm(forms.ModelForm):
    birthdate = forms.DateField(
        widget=forms.DateInput(attrs={'type': 'date'}, format='%Y-%m-%d'),
        input_formats=['%Y-%m-%d'],  # Optional, to ensure consistent parsing on submit
        required=True
    ) # Use <input type="date"> for selecting birthdate

    class Meta:
        model = Customer
        fields = ['full_name', 'birthdate', 'phone_number', 'email', 'address']

    def clean_phone_number(self):
        phone_number = self.cleaned_data.get('phone_number')
        validate_phone_number(phone_number)
        return phone_number

# Sale Transaction management
class SaleTransactionForm(forms.ModelForm):
    class Meta:
        model = SaleTransaction
        fields = [
            'transaction_number',
            'transaction_date',
            'customer',
            'discount',
            'cash_received',
            'payment_method',
            'remarks'
        ]
        widgets = {
            'transaction_date': forms.DateInput(
                attrs={'type': 'date'},
                format='%Y-%m-%d'
            ),
            'discount': forms.NumberInput(attrs={'step': '1'}),
            'cash_received': forms.NumberInput(attrs={'step': '1'}),
            'remarks': forms.Textarea(attrs={'rows': 2}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['customer'].widget = forms.HiddenInput()
        self.fields['discount'].initial = '0'
        self.fields['cash_received'].initial = '0'        
        self.fields['transaction_date'].input_formats = ['%Y-%m-%d']
        if not self.instance.pk:  # Only for new forms
            self.fields['transaction_date'].initial = timezone.now()

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
        self.fields['quantity'].widget.attrs.update({'disabled': 'disabled'})

class SaleScanForm(forms.Form):
    json_file = forms.FileField(label="Scan Sale JSON File", required=True)

# Reports management
class DateRangeForm(forms.Form):
    from_date = forms.DateField(widget=forms.DateInput(attrs={'type': 'date'}))
    to_date = forms.DateField(widget=forms.DateInput(attrs={'type': 'date'}))

# Discount management
class DiscountForm(forms.ModelForm):
    class Meta:
        model = Discount
        fields = ['name', 'products', 'percentage', 'from_date', 'to_date']
        widgets = {
            'products': forms.CheckboxSelectMultiple(),
            'from_date': forms.DateInput(attrs={'type': 'date'}),
            'to_date': forms.DateInput(attrs={'type': 'date'}),
        }

    def clean(self):
        cleaned_data = super().clean()
        if cleaned_data.get('from_date') > cleaned_data.get('to_date'):
            raise forms.ValidationError("From date must be before To date.")
        return cleaned_data
