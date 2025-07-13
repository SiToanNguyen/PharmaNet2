# home/views.py
import json
from datetime import date, timedelta
from reportlab.pdfgen import canvas
from reportlab.lib import colors
from io import BytesIO
from collections import defaultdict
from decimal import Decimal
from dateutil.relativedelta import relativedelta

from django.apps import apps
from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth import authenticate, login
from django.contrib.auth.forms import AuthenticationForm
from django.contrib.auth.models import User
from django.contrib import messages
from django.views.decorators.http import require_POST
from django.db import transaction
from django.db.models import Sum, F, Value, ExpressionWrapper, DecimalField, ForeignKey, DateTimeField, DateField, ManyToManyField, Count
from django.db.models.functions import Coalesce, TruncMonth
from django.http import JsonResponse, HttpResponse
from django.forms import modelformset_factory
from django.urls import reverse
from django.utils.dateparse import parse_date
from django.utils import timezone
from django.utils.timezone import now
from django.utils.safestring import mark_safe

from .models import (
    ActivityLog, Customer, 
    Manufacturer, Category, Product, Inventory, 
    PurchaseTransaction, PurchasedProduct, SaleTransaction, SoldProduct,
    Discount
)
from .forms import (
    UserCreationForm, UserEditForm, CustomerForm, DateRangeForm,
    ManufacturerForm, CategoryForm, ProductForm, 
    PurchaseTransactionForm, PurchasedProductForm, PurchaseScanForm,
    SaleTransactionForm, SoldProductForm, SaleScanForm,
    DiscountForm
)
from .utils import paginate_with_query_params, add_object, edit_object, delete_object, list_objects, log_activity, make_aware_datetime, format_value
from .decorators import superuser_required_403

# Homepage
def homepage(request):
    tab = request.GET.get('tab', 'expiring')
    today = date.today()
    cutoff_date = today + timedelta(days=30)

    # Shared context
    context = {
        'today': today,
        'active_tab': tab,
    }

    # Get expiring products count
    expiring_qs = Inventory.objects.filter(
        expiry_date__lte=cutoff_date,
        quantity__gt=0
    )
    context['expiring_count'] = expiring_qs.count()

    # Get low stock products count
    product_quantities = (
        Inventory.objects
        .values('product')
        .annotate(total_quantity=Sum('quantity'))
    )
    quantity_map = {entry['product']: entry['total_quantity'] for entry in product_quantities}

    low_stock_products = []
    for product in Product.objects.select_related('category'):
        total_qty = quantity_map.get(product.id, 0)
        if total_qty < product.category.low_stock_threshold:
            low_stock_products.append({
                'product': product,
                'total_quantity': total_qty,
            })
    context['low_stock_count'] = len(low_stock_products)

    # Tab-specific pagination
    if tab == 'expiring':
        inventory = (
            expiring_qs.select_related('product')
            .order_by('expiry_date')
        )
        for item in inventory:
            item.days_diff = (item.expiry_date - today).days
        page_obj, query = paginate_with_query_params(request, inventory, page_param='page')
        context['inventory_page_obj'] = page_obj
        context['inventory_query'] = query

    elif tab == 'lowstock':
        page_obj, query = paginate_with_query_params(request, low_stock_products, page_param='lowstockpage')
        context['low_stock_page_obj'] = page_obj
        context['low_stock_query'] = query

    return render(request, 'index.html', context)

# Activity Log
def activity_log_list(request):
    return list_objects(
        request,
        model=ActivityLog,
        columns=['timestamp', 'user', 'action', 'additional_info'],
        search_fields={
            'user': 'user__username', 
            'action': 'action', 
            'additional_info': 'additional_info'
        }
    )

# User management
def user_list(request):
    return list_objects(
        request,
        model=User,
        columns=['username', 'email', 'first_name', 'last_name', 'date_joined', 'last_login', 'is_active', 'is_staff', 'is_superuser'],
        search_fields={
            'username': 'username',
            'first_name': 'first_name',
            'last_name': 'last_name',
        },
        sort_fields={
            'date_joined': 'Date Joined', 
            'last_login': 'Last Login'
        },
        add=True,
        edit=True, 
        delete=True,
        related_model=ActivityLog,
        related_field_name='user',
        related_title='Activity Log',
        related_fields={
            'timestamp': 'Timestamp',
            'action': 'Action',
            'additional_info': 'Additional Info',
        }
    )

@superuser_required_403
def add_user(request):
    return add_object(
        request=request,
        form_class=UserCreationForm,
        model=User,
        success_url='user_list'
    )

@superuser_required_403
def edit_user(request, user_id):
    return edit_object(
        request=request,
        form_class=UserEditForm,
        model=User,
        object_id=user_id,
        success_url='user_list'
    )

@require_POST
@superuser_required_403
def delete_user(request, user_id):
    if delete_object(request, User, user_id):
        return redirect('user_list')
    return redirect('user_list')  # In case of error, just redirect

# Manufacturer management
def manufacturer_list(request):
    return list_objects(
        request,
        model=Manufacturer,
        columns=['name', 'address', 'phone_number', 'email'],
        search_fields={
            'name': 'name', 
            'address': 'address'
        },
        add=True,
        edit=True, 
        delete=True,
        related_model=PurchaseTransaction,
        related_field_name='manufacturer',
        related_title='Purchase Transactions',
        related_fields={
            'invoice_number': 'Invoice',
            'purchase_date': 'Date',
            'total_cost': 'Total (€)',
        }
    )

def add_manufacturer(request):
    return add_object(
        request=request,
        form_class=ManufacturerForm,
        model=Manufacturer,
        success_url='manufacturer_list'
    )

def edit_manufacturer(request, manufacturer_id):
    return edit_object(
        request=request,
        form_class=ManufacturerForm,
        model=Manufacturer,
        object_id=manufacturer_id,
        success_url='manufacturer_list'
    )

@require_POST
def delete_manufacturer(request, manufacturer_id):
    if delete_object(request, Manufacturer, manufacturer_id):
        return redirect('manufacturer_list')
    return redirect('manufacturer_list')  # In case of error, just redirect

# Category management
def category_list(request):
    return list_objects(
        request,
        model=Category,
        columns=['name', 'description', 'requires_prescription', 'low_stock_threshold'],
        search_fields={
            'name': 'name'
        },
        add=True,
        edit=True, 
        delete=True
    )

def add_category(request):
    return add_object(
        request=request,
        form_class=CategoryForm,
        model=Category,
        success_url='category_list'
    )

def edit_category(request, category_id):
    return edit_object(
        request=request,
        form_class=CategoryForm,
        model=Category,
        object_id=category_id,
        success_url='category_list'
    )

@require_POST
def delete_category(request, category_id):
    if delete_object(request, Category, category_id):
        return redirect('category_list')
    return redirect('category_list')  # In case of error, just redirect

# Product management
def product_list(request):
    products_with_stock = Product.objects.annotate(
        stock=Sum('inventory__quantity')
    )

    return list_objects(
        request,
        model=Product,
        columns=['name', 'category', 'manufacturer', 'sale_price', 'stock'],
        search_fields={
            'name': 'name', 
            'manufacturer': 'manufacturer__name'
        },
        sort_fields={
            'updated_at': 'Last Updated', 
            'stock': 'Stock'
        },
        add=True,
        edit=True, 
        delete=True,
        extra_context={'object_list': products_with_stock},
        related_model=Inventory,
        related_field_name='product',
        related_title='Inventory',
        related_fields={
            'quantity': 'Quantity',
            'expiry_date': 'Expiry Date',
        }
    )

def add_product(request):
    return add_object(
        request=request,
        form_class=ProductForm,
        model=Product,
        success_url='product_list'
    )

def edit_product(request, product_id):
    return edit_object(
        request=request,
        form_class=ProductForm,
        model=Product,
        object_id=product_id,
        success_url='product_list'
    )

@require_POST
def delete_product(request, product_id):
    if delete_object(request, Product, product_id):
        return redirect('product_list')
    return redirect('product_list')  # In case of error, just redirect

# Inventory management
def inventory_list(request):
    # Queryset with product and manufacturer preloaded
    base_qs = Inventory.objects.select_related('product__manufacturer').filter(quantity__gt=0)

    return list_objects(
        request,
        model=Inventory,
        columns = {
            'product': 'Product',
            'product.manufacturer': 'Manufacturer',
            'product.sale_price': 'Sale Price (€)',
            'quantity': 'Quantity',
            'expiry_date': 'Expiry Date',
        },
        search_fields={
            'product_name': 'product__name',
            'manufacturer_name': 'product__manufacturer__name'
        },
        sort_fields={
            'updated_at': 'Last Updated',
            'expiry_date': 'Expiry Date'
        },
        extra_context={
            'title': 'Inventory',
            'object_list': base_qs
        },
        delete=True
    )

@require_POST
def delete_inventory(request, inventory_id):
    inventory = get_object_or_404(Inventory, id=inventory_id)

    # Instead of deleting, set quantity to 0
    inventory.quantity = 0
    inventory.save()

    messages.success(request, f"Inventory '{inventory}' marked as zero quantity.")
    log_activity(user=request.user, action="deleted inventory item", additional_info=f"Inventory ID: {inventory.id}, Product: {inventory.product.name}")
    return redirect('inventory_list')

# Purchase Transactions management
def purchase_transaction_list(request):
    transactions = PurchaseTransaction.objects.prefetch_related('purchased_products').all()

    invoice_number_query = request.GET.get('invoice_number', '').strip()
    manufacturer_name_query = request.GET.get('manufacturer_name', '').strip()

    if invoice_number_query:
        transactions = transactions.filter(invoice_number__icontains=invoice_number_query)
    if manufacturer_name_query:
        transactions = transactions.filter(manufacturer__name__icontains=manufacturer_name_query)

    transactions = transactions.order_by('-purchase_date')

    scan_form = PurchaseScanForm()

    return list_objects(
        request,
        model=PurchaseTransaction,
        columns={
            'invoice_number': 'Invoice #',
            'manufacturer': 'Manufacturer',
            'purchase_date': 'Purchase Date',
            'total_cost': 'Total Cost (€)',
        },
        search_fields={
            'invoice_number': 'invoice_number',
            'manufacturer_name': 'manufacturer__name',
        },
        sort_fields={
            'purchase_date': 'Purchase Date',
            'total_cost': 'Total Cost',
        },
        add=True,
        delete=True,
        extra_context={
            'title': 'Purchase Transaction',
            'object_list': transactions,
            'scan_form': scan_form,
            'scan_view_name': 'scan_purchase_transaction',
        },
        related_model=PurchasedProduct,
        related_field_name='purchase_transaction',
        related_title='Purchased Products',
        related_fields={
            'product': 'Product',
            'quantity': 'Quantity',
            'purchase_price': 'Purchase Price (€)',
            'batch_number': 'Batch #',
            'expiry_date': 'Expiry Date',
        }
    )

def add_purchase_transaction(request):
    PurchasedProductFormSet = modelformset_factory(
        PurchasedProduct, form=PurchasedProductForm, extra=1, can_delete=True
    )

    if request.method == "POST":
        form = PurchaseTransactionForm(request.POST)
        formset = PurchasedProductFormSet(request.POST, prefix="products")

        # Set correct queryset for product fields before validation
        manufacturer_id = request.POST.get("manufacturer")
        if manufacturer_id:
            try:
                manufacturer_id = int(manufacturer_id)
                product_qs = Product.objects.filter(manufacturer_id=manufacturer_id)
            except (ValueError, TypeError):
                product_qs = Product.objects.none()
        else:
            product_qs = Product.objects.none()

        for subform in formset:
            subform.fields['product'].queryset = product_qs

        # Validate the form and formset
        if form.is_valid() and formset.is_valid():
            purchase_transaction = form.save(commit=False)
            purchase_transaction.total_cost = 0  # Initialize total cost
            purchase_transaction.created_by = request.user if request.user.is_authenticated else None

            purchase_transaction.save()

            # Save purchased products
            for product_form in formset:
                if product_form.cleaned_data and not product_form.cleaned_data.get('DELETE', False):
                    purchased_product = product_form.save(commit=False)
                    purchased_product.purchase_transaction = purchase_transaction
                    purchased_product.purchase_price = product_form.cleaned_data.get('purchase_price', 0) or 0  # Default to 0 if missing
                    purchased_product.save()

                    purchase_transaction.total_cost += purchased_product.total_price or 0  # Handle None values safely

            purchase_transaction.save()

            for purchased_product in purchase_transaction.purchased_products.all():
                inventory_item, created = Inventory.objects.get_or_create(
                    product=purchased_product.product,
                    expiry_date=purchased_product.expiry_date,
                    defaults={'quantity': purchased_product.quantity}
                )
                if not created:
                    inventory_item.quantity += purchased_product.quantity
                    inventory_item.save()

            log_activity(
                user=request.user,
                action="added purchase transaction",
                additional_info=f"Invoice #{purchase_transaction.invoice_number}, Manufacturer: {purchase_transaction.manufacturer.name}"
            )
                    
            messages.success(request, f"Purchase transaction {purchase_transaction.invoice_number} added.")
            return redirect('purchase_transaction_list')

        return render(request, "add_purchase_transaction.html", {
            "form": form,
            "formset": formset,
            "manufacturers": Manufacturer.objects.all(),
            "errors": form.errors,
            "formset_errors": formset.errors,
        })

    else: # request.method != "POST"
        form = PurchaseTransactionForm()
        formset = PurchasedProductFormSet(queryset=PurchasedProduct.objects.none(), prefix="products")
        for subform in formset:
            subform.fields['product'].queryset = Product.objects.none()
        formset.empty_form.fields['product'].queryset = Product.objects.none()

    return render(request, "add_purchase_transaction.html", {
        "form": form,
        "formset": formset,
        "manufacturers": Manufacturer.objects.all(),
        "errors": form.errors,
        "formset_errors": formset.errors,
        "success_url": reverse("purchase_transaction_list"),
    })

def get_products_by_manufacturer(request):
    manufacturer_id = request.GET.get('manufacturer_id')
    if manufacturer_id:
        products = Product.objects.filter(manufacturer_id=manufacturer_id)
        product_data = list(products.values('id', 'name'))
        return JsonResponse(product_data, safe=False)
    return JsonResponse({'error': 'No manufacturer selected'}, status=400)

@require_POST
def scan_purchase_transaction(request):
    scan_form = PurchaseScanForm(request.POST, request.FILES)
    if scan_form.is_valid():
        json_file = scan_form.cleaned_data['json_file']
        try:
            data = json.load(json_file)
            required_fields = {"invoice_number", "manufacturer", "purchase_date", "total_cost", "products"}
            if not required_fields.issubset(data.keys()):
                messages.error(request, "Missing required fields in JSON.")
                return redirect("purchase_transaction_list")

            manufacturer = Manufacturer.objects.filter(name=data["manufacturer"]).first()
            if not manufacturer:
                messages.error(request, f"Manufacturer '{data['manufacturer']}' not found.")
                return redirect("purchase_transaction_list")

            if PurchaseTransaction.objects.filter(invoice_number=data["invoice_number"]).exists():
                messages.error(request, f"Invoice number {data['invoice_number']} already exists.")
                return redirect("purchase_transaction_list")

            transaction = PurchaseTransaction.objects.create(
                invoice_number=data["invoice_number"],
                manufacturer=manufacturer,
                purchase_date=make_aware_datetime(data["purchase_date"]),
                total_cost=data["total_cost"],
                remarks=data.get("remarks", ""),
                created_by=request.user if request.user.is_authenticated else None
            )

            for item in data["products"]:
                product = Product.objects.filter(name=item["product"], manufacturer=manufacturer).first()
                if not product:
                    transaction.delete()
                    messages.error(request, f"Product not found: {item['product']}")
                    return redirect("purchase_transaction_list")

                PurchasedProduct.objects.create(
                    purchase_transaction=transaction,
                    product=product,
                    batch_number=item.get("batch_number", ""),
                    quantity=item["quantity"],
                    purchase_price=item["purchase_price"],
                    expiry_date=parse_date(item["expiry_date"])
                )

            for purchased_product in transaction.purchased_products.all():
                inventory_item, created = Inventory.objects.get_or_create(
                    product=purchased_product.product,
                    expiry_date=purchased_product.expiry_date,
                    defaults={'quantity': purchased_product.quantity}
                )
                if not created:
                    inventory_item.quantity += purchased_product.quantity
                    inventory_item.save()

            log_activity(
                user=request.user,
                action="scanned purchase transaction",
                additional_info=f"Invoice #{transaction.invoice_number}, Manufacturer: {transaction.manufacturer.name}"
            )
            
            messages.success(request, f"Purchase transaction {transaction.invoice_number} scanned successfully.")
            return redirect("purchase_transaction_list")

        except Exception as e:
            messages.error(request, f"Error processing JSON: {str(e)}")
            return redirect("purchase_transaction_list")
    else:
        messages.error(request, "Invalid file uploaded.")
        return redirect("purchase_transaction_list")

@require_POST
def delete_purchase_transaction(request, transaction_id):
    transaction = get_object_or_404(PurchaseTransaction, id=transaction_id)

    # Check if inventory has enough quantity to allow deletion
    for purchased_product in transaction.purchased_products.all():
        try:
            inventory = Inventory.objects.get(
                product=purchased_product.product,
                expiry_date=purchased_product.expiry_date
            )
        except Inventory.DoesNotExist:
            messages.error(request, "Cannot delete: Matching inventory item not found.")
            return redirect('purchase_transaction_list')

        if inventory.quantity < purchased_product.quantity:
            messages.error(request, f"Cannot delete: Insufficient inventory for {purchased_product.product.name}.")
            return redirect('purchase_transaction_list')

    # Roll back the inventory
    for purchased_product in transaction.purchased_products.all():
        inventory = Inventory.objects.get(
            product=purchased_product.product,
            expiry_date=purchased_product.expiry_date
        )
        inventory.quantity -= purchased_product.quantity
        inventory.save()

    transaction.delete()

    log_activity(
        user=request.user,
        action="deleted purchase transaction",
        additional_info=f"Invoice #{transaction.invoice_number}, Manufacturer: {transaction.manufacturer.name}"
    )

    messages.success(request, f"Purchase transaction {transaction.invoice_number} deleted and inventory updated.")
    return redirect('purchase_transaction_list')

# Customer management
def customer_list(request):
    customers_with_transaction = Customer.objects.annotate(
        transactions=Count('saletransaction')
    )
    return list_objects(
        request,
        model=Customer,
        columns=['full_name', 'birthdate', 'phone_number', 'email', 'address', 'transactions'],
        search_fields={
            'name': 'full_name'
        },
        add=True,
        edit=True, 
        delete=True,
        extra_context={'object_list': customers_with_transaction},
        related_model=SaleTransaction,
        related_field_name='customer',
        related_title='Sale Transactions',
        related_fields={
            'transaction_number': 'Transaction #',
            'transaction_date': 'Date',
            'price': 'Price (€)',
            'discount': 'Discount (€)',
            'total': 'Total (€)',
            'cash_received': 'Cash Received (€)',
            'payment_method': 'Payment Method',
        }
    )

def add_customer(request):
    return add_object(
        request=request,
        form_class=CustomerForm,
        model=Customer,
        success_url='customer_list'
    )

def edit_customer(request, customer_id):
    return edit_object(
        request=request,
        form_class=CustomerForm,
        model=Customer,
        object_id=customer_id,
        success_url='customer_list'
    )

@require_POST
def delete_customer(request, customer_id):
    if delete_object(request, Customer, customer_id):
        return redirect('customer_list')
    return redirect('customer_list')

# Sale Transaction management
def sale_transaction_list(request):
    transactions = SaleTransaction.objects.prefetch_related('sold_products').all()

    transaction_number_query = request.GET.get('transaction_number', '').strip()
    customer_name_query = request.GET.get('customer_name', '').strip()

    if transaction_number_query:
        transactions = transactions.filter(transaction_number__icontains=transaction_number_query)
    if customer_name_query:
        transactions = transactions.filter(customer__full_name__icontains=customer_name_query)

    transactions = transactions.order_by('-transaction_date')

    scan_form = SaleScanForm()

    return list_objects(
        request,
        model=SaleTransaction,
        columns={
            'transaction_number': 'Transaction #',
            'customer': 'Customer',
            'transaction_date': 'Date',
            'price': 'Price (€)',
            'discount': 'Discount (€)',
            'total': 'Total (€)',
            'cash_received': 'Cash (€)',
            'payment_method': 'Payment Method',
        },
        search_fields={
            'transaction_number': 'transaction_number',
            'customer_name': 'customer__full_name',
        },
        sort_fields={
            'transaction_date': 'Date',
            'price': 'Price',
            'discount': 'Discount',
        },
        add=True,
        delete=True,
        extra_context={
            'title': 'Sale Transaction',
            'object_list': transactions,
            'scan_form': scan_form,
            'scan_view_name': 'scan_sale_transaction',
        },
        related_model=SoldProduct,
        related_field_name='sale_transaction',
        related_title='Sold Products',
        related_fields={
            'inventory_item': 'Inventory Item',
            'quantity': 'Quantity',
            'sale_price': 'Sale Price (€)',
        }
    )

def add_sale_transaction(request):
    SoldProductFormSet = modelformset_factory(
        SoldProduct, form=SoldProductForm, extra=1, can_delete=True
    )

    if request.method == "POST":
        form = SaleTransactionForm(request.POST)
        formset = SoldProductFormSet(request.POST, prefix="products")

        if form.is_valid() and formset.is_valid():
            try:
                with transaction.atomic():
                    sale_transaction = form.save(commit=False)
                    sale_transaction.transaction_date = timezone.localtime(timezone.now())
                    sale_transaction.created_by = request.user if request.user.is_authenticated else None
                    sale_transaction.price = 0  # sum of all SoldProduct total_price
                    sale_transaction.total = 0  # total after discount

                    sale_transaction.save()

                    # Handle sold products
                    for sold_form in formset:
                        if sold_form.cleaned_data and not sold_form.cleaned_data.get('DELETE', False):
                            sold_product = sold_form.save(commit=False)
                            sold_product.sale_transaction = sale_transaction
                            product = sold_product.inventory_item.product
                            sale_date = sale_transaction.transaction_date.date()

                            # Check for valid discount
                            discount_qs = product.discounts.filter(from_date__lte=sale_date, to_date__gte=sale_date)
                            if discount_qs.exists():
                                total_percentage = sum([d.percentage for d in discount_qs])
                                total_percentage = min(total_percentage, Decimal('100.00'))
                                discounted_price = product.sale_price * (Decimal('1.00') - total_percentage / Decimal('100.00'))
                                sold_product.sale_price = round(discounted_price, 2)
                            else:
                                sold_product.sale_price = product.sale_price

                            sold_product.save()

                            # Calculate total price
                            sale_transaction.price += sold_product.total_price or 0
                            sale_transaction.total = sale_transaction.price - sale_transaction.discount

                            # Subtract quantity from Inventory
                            # Prevent multiple threads from overselling the same inventory item by making sure only one thread can touch that inventory row at a time.
                            inventory_qs = Inventory.objects.select_for_update().get(id=sold_product.inventory_item.id)

                            if inventory_qs.quantity < sold_product.quantity:
                                raise Exception(f"Not enough stock for {inventory_qs.product.name} (only {inventory_qs.quantity} available)")

                            inventory_qs.quantity -= sold_product.quantity
                            inventory_qs.save()

                    sale_transaction.save()  # update with final price

                    log_activity(
                        user=request.user,
                        action="added sale transaction",
                        additional_info=f"Transaction #{sale_transaction.transaction_number}"
                    )

                    messages.success(request, f"Sale transaction {sale_transaction.transaction_number} added.")
                    return redirect('sale_transaction_list')

            except Exception as e:
                messages.error(request, f"Error saving transaction: {e}")
                return render(request, "add_sale_transaction.html", { # POST request with a valid form, but a backend failure (except block)
                    "form": form,
                    "formset": formset,
                    "customers": Customer.objects.all(),
                    "inventory_items": Inventory.objects.select_related('product', 'product__manufacturer').filter(quantity__gt=0),
                    "errors": form.errors,
                    "formset_errors": formset.errors,
                    "success_url": reverse("sale_transaction_list"),
                })

        return render(request, "add_sale_transaction.html", { # POST request with form/formset errors
            "form": form,
            "formset": formset,
            "customers": Customer.objects.all(),
            "inventory_items": Inventory.objects.select_related('product', 'product__manufacturer').filter(quantity__gt=0),
            "errors": form.errors,
            "formset_errors": formset.errors,            
            "success_url": reverse("sale_transaction_list"),
        })

    else:
        form = SaleTransactionForm()
        formset = SoldProductFormSet(queryset=SoldProduct.objects.none(), prefix="products")

    return render(request, "add_sale_transaction.html", { # GET request (initial form page)
        "form": form,
        "formset": formset,
        "customers": Customer.objects.all(),
        "inventory_items": Inventory.objects.select_related('product', 'product__manufacturer').filter(quantity__gt=0),
        "errors": form.errors,
        "formset_errors": formset.errors,
        "success_url": reverse("sale_transaction_list"),
    })

def get_inventory_price(request, inventory_id):
    try:
        item = Inventory.objects.get(id=inventory_id)
        return JsonResponse({
            'price': item.product.sale_price,
            'available_quantity': item.quantity
        })
    except Inventory.DoesNotExist:
        return JsonResponse({'error': 'Not found'}, status=404)

@require_POST
def scan_sale_transaction(request):
    scan_form = SaleScanForm(request.POST, request.FILES)
    if scan_form.is_valid():
        json_file = scan_form.cleaned_data['json_file']
        try:
            data = json.load(json_file)
            required_fields = {"transaction_number", "transaction_date", "price", "discount", "cash_received", "payment_method", "products"}
            if not required_fields.issubset(data.keys()):
                messages.error(request, "Missing required fields in JSON.")
                return redirect("sale_transaction_list")

            # Check if transaction number already exists
            if SaleTransaction.objects.filter(transaction_number=data["transaction_number"]).exists():
                messages.error(request, f"Transaction number {data['transaction_number']} already exists.")
                return redirect("sale_transaction_list")

            # Optional: customer
            customer = None
            if data.get("customer"):
                customer_name = data["customer"].strip()
                customer, created = Customer.objects.get_or_create(full_name=customer_name)
                if created and request.user.is_authenticated:
                    log_activity(
                        user=request.user,
                        action="added customer via scan",
                        additional_info=f"Customer '{customer.full_name}' added during scanned sale transaction"
                    )

            transaction = SaleTransaction.objects.create(
                transaction_number=data["transaction_number"],
                customer=customer,
                transaction_date=make_aware_datetime(data["transaction_date"]),
                price=data["price"],
                discount=data["discount"],
                total=data["price"] - data["discount"],
                cash_received=data["cash_received"],
                payment_method=data["payment_method"],
                remarks=data.get("remarks", ""),
                created_by=request.user if request.user.is_authenticated else None
            )

            for item in data["products"]:
                try:
                    inventory = Inventory.objects.get(id=item["inventory_id"])
                except Inventory.DoesNotExist:
                    transaction.delete()
                    messages.error(request, f"Inventory item with ID {item['inventory_id']} not found.")
                    return redirect("sale_transaction_list")

                if inventory.quantity < item["quantity"]:
                    transaction.delete()
                    messages.error(request, f"Not enough stock for {inventory.product.name}.")
                    return redirect("sale_transaction_list")

                SoldProduct.objects.create(
                    sale_transaction=transaction,
                    inventory_item=inventory,
                    quantity=item["quantity"],
                    sale_price=item.get("sale_price", inventory.product.sale_price)
                )

                inventory.quantity -= item["quantity"]
                inventory.save()

            log_activity(
                user=request.user,
                action="scanned sale transaction",
                additional_info=f"Transaction #{transaction.transaction_number}"
            )

            messages.success(request, f"Sale transaction {transaction.transaction_number} scanned successfully.")
            return redirect("sale_transaction_list")

        except Exception as e:
            messages.error(request, f"Error processing JSON: {str(e)}")
            return redirect("sale_transaction_list")

    else:
        messages.error(request, "Invalid file uploaded.")
        return redirect("sale_transaction_list")

@require_POST
def delete_sale_transaction(request, transaction_id):
    transaction = get_object_or_404(SaleTransaction, id=transaction_id)

    # Check if all sold products still exist in Product table
    for sold_product in transaction.sold_products.all():
        product = sold_product.inventory_item.product
        if not Product.objects.filter(id=product.id).exists():
            messages.error(request, f"Cannot delete: Product '{product.name}' no longer exists in the system.")
            return redirect('sale_transaction_list')

    # Roll back the inventory
    for sold_product in transaction.sold_products.all():
        inventory = sold_product.inventory_item
        inventory.quantity += sold_product.quantity
        inventory.save()

    transaction.delete()

    log_activity(
        user=request.user,
        action="deleted sale transaction",
        additional_info=f"Transaction #{transaction.transaction_number}"
    )

    messages.success(request, f"Sale transaction {transaction.transaction_number} deleted and inventory updated.")
    return redirect('sale_transaction_list')

def report(request):
    tab = request.GET.get('tab', 'summary')
    
    # Shared context
    context = {
        'active_tab': tab,
    }

    # Financial Summary
    total_purchase = 0
    total_sales = 0
    total_discount = 0
    profit = 0
    form = DateRangeForm(request.GET if 'generate' in request.GET else None)

    product_summary = []

    if form.is_valid():
        from_date = form.cleaned_data['from_date']
        to_date = form.cleaned_data['to_date']

        purchases = PurchaseTransaction.objects.filter(purchase_date__date__range=(from_date, to_date))
        sales = SaleTransaction.objects.filter(transaction_date__date__range=(from_date, to_date))

        total_purchase = purchases.aggregate(Sum('total_cost'))['total_cost__sum'] or 0
        total_sales = sales.aggregate(Sum('total'))['total__sum'] or 0
        profit = total_sales - total_purchase
        total_discount = sales.aggregate(Sum('discount'))['discount__sum'] or 0

        product_summary = defaultdict(lambda: {
            'purchased_quantity': 0,
            'total_spent': 0,
            'sold_quantity': 0,
            'total_earned': 0,
            'total_discount': 0
        })

        # Purchased Products
        purchased_summary = (
            PurchasedProduct.objects
            .filter(purchase_transaction__purchase_date__date__range=(from_date, to_date))
            .values(name=F('product__name'))
            .annotate(
                total_quantity=Coalesce(Sum('quantity'), Value(0)),
                total_spent=Coalesce(
                    Sum(
                        ExpressionWrapper(
                            F('quantity') * F('purchase_price'),
                            output_field=DecimalField(max_digits=15, decimal_places=2)
                        )
                    ),
                    Value(0, output_field=DecimalField(max_digits=15, decimal_places=2))
                )
            )
            .order_by('name')
        )

        # Sold Products
        sold_summary = (
            SoldProduct.objects
            .filter(sale_transaction__transaction_date__date__range=(from_date, to_date))
            .values(name=F('inventory_item__product__name'))
            .annotate(
                total_quantity=Coalesce(Sum('quantity'), Value(0)),
                total_earned=Coalesce(
                    Sum(
                        ExpressionWrapper(
                            F('quantity') * F('sale_price'),
                            output_field=DecimalField(max_digits=15, decimal_places=2)
                        )
                    ),
                    Value(0, output_field=DecimalField(max_digits=15, decimal_places=2))
                )
            )
            .order_by('name')
        )

        # Initialize merge container
        product_summary_dict = defaultdict(lambda: {
            'purchased_quantity': 0,
            'total_spent': 0,
            'sold_quantity': 0,
            'total_earned': 0
        })

        # Merge purchase data
        for item in purchased_summary:
            name = item['name']
            product_summary_dict[name]['purchased_quantity'] = item['total_quantity']
            product_summary_dict[name]['total_spent'] = item['total_spent']

        # Merge sales data
        for item in sold_summary:
            name = item['name']
            product_summary_dict[name]['sold_quantity'] = item['total_quantity']
            product_summary_dict[name]['total_earned'] = item['total_earned']

        # Convert to sorted list
        product_summary = [
            {
                'name': name,
                'purchased_quantity': data['purchased_quantity'],
                'sold_quantity': data['sold_quantity'],
                'total_spent': data['total_spent'],
                'total_earned': data['total_earned'],
                'profit': data['total_earned'] - data['total_spent']
            }
            for name, data in sorted(product_summary_dict.items())
        ]

        # Sort by profit in descending order
        product_summary.sort(key=lambda x: x['profit'], reverse=True)

    context.update({
        'form': form,
        'total_purchase': total_purchase,
        'total_sales': total_sales,
        'total_discount': total_discount,
        'profit': profit,
        'product_summary': product_summary,
    })

    # Revenue Chart
    months = int(request.GET.get('months', 12))

    # Today = first day of current month (e.g. 2025-07-01)
    today = now().date().replace(day=1)

    # Start month = first day of the month exactly `months` ago (exclude current month)
    start_month = today - relativedelta(months=months)

    # Aggregate purchases by month
    purchases = (
        PurchaseTransaction.objects
        .filter(purchase_date__date__gte=start_month, purchase_date__date__lt=today)
        .annotate(month=TruncMonth('purchase_date'))
        .values('month')
        .annotate(total=Coalesce(Sum('total_cost', output_field=DecimalField()), Value(0), output_field=DecimalField()))
    )

    # Aggregate sales by month
    sales = (
        SaleTransaction.objects
        .filter(transaction_date__date__gte=start_month, transaction_date__date__lt=today)
        .annotate(month=TruncMonth('transaction_date'))
        .values('month')
        .annotate(total=Coalesce(Sum('total', output_field=DecimalField()), Value(0), output_field=DecimalField()))
    )

    purchase_map = {item['month'].strftime('%Y-%m'): float(item['total']) for item in purchases}
    sales_map = {item['month'].strftime('%Y-%m'): float(item['total']) for item in sales}

    labels, purchase_vals, sales_vals, profit_vals = [], [], [], []

    for i in range(months):
        date_iter = start_month + relativedelta(months=i)
        label = date_iter.strftime('%b %Y')
        key = date_iter.strftime('%Y-%m')
        p = purchase_map.get(key, 0)
        s = sales_map.get(key, 0)
        labels.append(label)
        purchase_vals.append(p)
        sales_vals.append(s)
        profit_vals.append(s - p)

    chart_data = {
        'labels': labels,
        'purchase': purchase_vals,
        'sales': sales_vals,
        'profit': profit_vals,
        'colors': {
            'purchase': request.GET.get('purchase_color', 'red'),
            'sales': request.GET.get('sales_color', 'blue'),
            'profit': request.GET.get('profit_color', 'gray'),
        }
    }

    context.update({
        'months': months,
        'chart_data': mark_safe(json.dumps(chart_data)),
    })

    return render(request, 'report.html', context)

def export_to_pdf(request):
    form = DateRangeForm(request.GET or None)

    if not (form and form.is_valid()):
        print("[DEBUG] Export PDF form is invalid.")
        print("[DEBUG] GET data:", request.GET.dict())
        print("[DEBUG] Form errors:", form.errors.as_json())
        return redirect('reports')

    from_date = form.cleaned_data['from_date']
    to_date = form.cleaned_data['to_date']

    total_purchase = 0
    total_sales = 0
    total_discount = 0
    profit = 0

    purchases = PurchaseTransaction.objects.filter(purchase_date__date__range=(from_date, to_date))
    sales = SaleTransaction.objects.filter(transaction_date__date__range=(from_date, to_date))

    total_purchase = purchases.aggregate(Sum('total_cost'))['total_cost__sum'] or 0
    total_sales = sales.aggregate(Sum('total'))['total__sum'] or 0
    total_discount = sales.aggregate(Sum('discount'))['discount__sum'] or 0
    profit = total_sales - total_purchase

    # Product summary calculation
    purchased_summary = (
        PurchasedProduct.objects
        .filter(purchase_transaction__purchase_date__date__range=(from_date, to_date))
        .values(name=F('product__name'))
        .annotate(
            total_quantity=Coalesce(Sum('quantity'), Value(0)),
            total_spent=Coalesce(
                Sum(
                    ExpressionWrapper(
                        F('quantity') * F('purchase_price'),
                        output_field=DecimalField(max_digits=15, decimal_places=2)
                    )
                ),
                Value(0, output_field=DecimalField(max_digits=15, decimal_places=2))
            )
        )
    )

    sold_summary = (
        SoldProduct.objects
        .filter(sale_transaction__transaction_date__date__range=(from_date, to_date))
        .values(name=F('inventory_item__product__name'))
        .annotate(
            total_quantity=Coalesce(Sum('quantity'), Value(0)),
            total_earned=Coalesce(
                Sum(
                    ExpressionWrapper(
                        F('quantity') * F('sale_price'),
                        output_field=DecimalField(max_digits=15, decimal_places=2)
                    )
                ),
                Value(0, output_field=DecimalField(max_digits=15, decimal_places=2))
            )
        )
    )

    product_summary_dict = defaultdict(lambda: {
        'purchased_quantity': 0,
        'total_spent': 0,
        'sold_quantity': 0,
        'total_earned': 0
    })

    for item in purchased_summary:
        name = item['name']
        product_summary_dict[name]['purchased_quantity'] = item['total_quantity']
        product_summary_dict[name]['total_spent'] = item['total_spent']

    for item in sold_summary:
        name = item['name']
        product_summary_dict[name]['sold_quantity'] = item['total_quantity']
        product_summary_dict[name]['total_earned'] = item['total_earned']

    product_summary = [
        {
            'name': name,
            'purchased_quantity': data['purchased_quantity'],
            'sold_quantity': data['sold_quantity'],
            'total_spent': data['total_spent'],
            'total_earned': data['total_earned'],
            'profit': data['total_earned'] - data['total_spent']
        }
        for name, data in product_summary_dict.items()
    ]

    product_summary.sort(key=lambda x: x['profit'], reverse=True)

    # Generate PDF
    buffer = BytesIO()
    p = canvas.Canvas(buffer)
    header_y = 800
    line_height = 20

    p.setFont("Helvetica-Bold", 14)
    p.drawString(100, header_y, "Financial Summary Report")
    header_y -= line_height

    p.setFont("Helvetica", 12)
    p.drawString(100, header_y, f"Date Range: {from_date.strftime('%B %d, %Y')} to {to_date.strftime('%B %d, %Y')}")
    header_y -= line_height

    p.drawString(100, header_y, f"Total Purchase Cost: € {total_purchase:,.2f}")
    header_y -= line_height

    p.drawString(100, header_y, f"Total Sales Revenue: € {total_sales:,.2f}")
    header_y -= line_height

    p.drawString(100, header_y, f"Estimated Profit: € {profit:,.2f}")
    header_y -= line_height

    p.drawString(100, header_y, f"Total Discount: € {total_discount:,.2f}")
    header_y -= line_height


    # Product summary table
    y = header_y - 20
    p.setFont("Helvetica-Bold", 12)
    p.drawString(40, y, "Product Summary:")
    y -= 20
    p.setFont("Helvetica-Bold", 10)

    # Define column positions (x coordinates)
    x_name = 40
    x_bought = 260
    x_sold = 310
    x_spent = 360
    x_earned = 430
    x_profit = 500
    col_width = 50  # for centering numbers
    row_height = 15

    # Draw headers
    p.drawString(x_name, y, "Name")
    p.drawCentredString(x_bought + col_width // 2, y, "Bought")
    p.drawCentredString(x_sold + col_width // 2, y, "Sold")
    p.drawCentredString(x_spent + col_width // 2, y, "Spent (€)")
    p.drawCentredString(x_earned + col_width // 2, y, "Earned (€)")
    p.drawCentredString(x_profit + col_width // 2, y, "Profit (€)")
    y -= 15

    p.setFont("Helvetica", 10)
    page_num = 1
    row_index = 1  # For zebra striping
    for item in product_summary:
        if y < 60:
            # Draw page number before moving to next page
            draw_page_number(p, page_num)
            p.showPage()
            page_num += 1
            y = 800
            p.setFont("Helvetica-Bold", 10)
            p.drawString(x_name, y, "Name")
            p.drawCentredString(x_bought + col_width // 2, y, "Bought")
            p.drawCentredString(x_sold + col_width // 2, y, "Sold")
            p.drawCentredString(x_spent + col_width // 2, y, "Spent (€)")
            p.drawCentredString(x_earned + col_width // 2, y, "Earned (€)")
            p.drawCentredString(x_profit + col_width // 2, y, "Profit (€)")
            y -= 15
            p.setFont("Helvetica", 10)

        # Zebra stripe for even-numbered rows
        if row_index % 2 == 0:
            p.setFillColor(colors.lightgrey)
            p.rect(x_name - 2, y - 2, 540, row_height, fill=1, stroke=0)
            p.setFillColor(colors.black)  # Reset to default text color
        
        # Name left-aligned, numbers centered in their columns
        p.drawString(x_name, y, str(item['name'])[:32])
        p.drawCentredString(x_bought + col_width // 2, y, str(item['purchased_quantity']))
        p.drawCentredString(x_sold + col_width // 2, y, str(item['sold_quantity']))
        p.drawCentredString(x_spent + col_width // 2, y, f"{item['total_spent']:,.2f}")
        p.drawCentredString(x_earned + col_width // 2, y, f"{item['total_earned']:,.2f}")
        p.drawCentredString(x_profit + col_width // 2, y, f"{item['profit']:,.2f}")

        y -= row_height
        row_index += 1

    # Draw page number on the last page
    draw_page_number(p, page_num)
    p.save()

    buffer.seek(0)
    response = HttpResponse(buffer, content_type='application/pdf')
    response['Content-Disposition'] = 'attachment; filename="financial_summary.pdf"'
    return response

def draw_page_number(canvas_obj, page_number):
    canvas_obj.setFont("Helvetica", 9)
    text = f"{page_number}"
    width = canvas_obj._pagesize[0]
    canvas_obj.drawRightString(width - 40, 20, text)

def get_object_details(request, model_name, pk):
    # Normalize model name: "activity log" -> "ActivityLog"
    normalized_name = ''.join(word.capitalize() for word in model_name.split())

    try:
        if normalized_name.lower() == 'user':
            model = apps.get_model('auth', 'User')
            exclude_fields = ['password']
        else:
            model = apps.get_model('home', normalized_name)
            exclude_fields = []
    except LookupError:
        return JsonResponse({'error': f'Model "{model_name}" not found'}, status=404)

    try:
        obj = model.objects.get(pk=pk)
        data = {}

        for field in model._meta.fields:
            if field.name in exclude_fields:
                continue

            value = getattr(obj, field.name)

            if isinstance(field, ForeignKey):
                display_value = str(value) if value else None
            elif isinstance(field, DateTimeField):
                if value:
                    time_str = value.strftime('%I:%M %p').lstrip('0').lower()
                    time_str = time_str.replace('am', 'a.m.').replace('pm', 'p.m.')
                    display_value = value.strftime('%d %b %Y') + ', ' + time_str
                else:
                    display_value = None
            elif isinstance(field, DateField):
                display_value = value.strftime('%d %b %Y') if value else None
            else:
                display_value = value

            label = field.verbose_name.title()
            if label == "Id":
                label = "ID"

            data[label] = display_value

        # === Related list support ===
        related_model_name = request.GET.get("related_model")
        related_field_name = request.GET.get("related_field")
        related_fields = request.GET.getlist("related_fields")

        if related_model_name and related_field_name:
            try:
                RelatedModel = apps.get_model("home", related_model_name)

                # Determine if M2M or FK
                field = RelatedModel._meta.get_field(related_field_name)

                if isinstance(field, ManyToManyField):
                    related_objects = getattr(obj, related_field_name).all()
                else:  # Assume FK
                    related_objects = RelatedModel.objects.filter(**{f"{related_field_name}__id": obj.id})

                related_data = []
                for item in related_objects:
                    item_data = {}
                    for field_name in related_fields:
                        raw_value = getattr(item, field_name, None)
                        print("Calling format_value for:", field_name, raw_value, type(raw_value))
                        display_value = format_value(raw_value)
                        item_data[field_name.replace("_", " ").title()] = display_value

                    related_data.append(item_data)

                data["_related_list"] = related_data

            except LookupError:
                data["_related_list_error"] = f"Related model {related_model_name} not found."
            except Exception as e:
                data["_related_list_error"] = str(e)

        return JsonResponse(data)

    except model.DoesNotExist:
        return JsonResponse({'error': 'Object not found'}, status=404)
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)
    
def get_related_list(request, related_model_name, parent_model_name, parent_id):
    try:
        # Special case for the Django default User model
        if related_model_name.lower() == 'user':
            RelatedModel = apps.get_model('auth', 'User')
        else:
            RelatedModel = apps.get_model('home', related_model_name.capitalize())

        if parent_model_name.lower() == 'user':
            ParentModel = apps.get_model('auth', 'User')
        else:
            ParentModel = apps.get_model('home', parent_model_name.capitalize())
    except LookupError as e:
        return JsonResponse({'error': str(e)}, status=404)

    try:
        # Try to find a ForeignKey from RelatedModel → ParentModel
        fk_field_name = None
        for field in RelatedModel._meta.fields:
            if isinstance(field, ForeignKey) and field.related_model == ParentModel:
                fk_field_name = field.name
                break

        if fk_field_name:
            # ForeignKey relationship (normal case)
            related_objects = RelatedModel.objects.filter(**{f"{fk_field_name}__id": parent_id})
        else:
            # Try reverse ManyToManyField: ParentModel has a M2M to RelatedModel
            parent_obj = ParentModel.objects.get(id=parent_id)

            found = False
            for field in ParentModel._meta.many_to_many:
                if field.related_model == RelatedModel:
                    related_objects = getattr(parent_obj, field.name).all()
                    found = True
                    break

            if not found:
                return JsonResponse({'error': f'No FK or reverse M2M between {parent_model_name} and {related_model_name}'}, status=400)

        page_obj, query_string = paginate_with_query_params(request, related_objects)
        
        data = {
            'results': [
                {field.name: str(getattr(obj, field.name)) for field in RelatedModel._meta.fields}
                for obj in page_obj
            ],
            'pagination': {
                'has_previous': page_obj.has_previous(),
                'has_next': page_obj.has_next(),
                'current_page': page_obj.number,
                'total_pages': page_obj.paginator.num_pages,
                'total_items': page_obj.paginator.count,
                'previous_page_number': page_obj.previous_page_number() if page_obj.has_previous() else None,
                'next_page_number': page_obj.next_page_number() if page_obj.has_next() else None,
            },
            'query_string': query_string,
        }
        return JsonResponse(data, safe=False)

    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)

# Discount management
def discount_list(request):
    return list_objects(
        request,
        model=Discount,
        columns=['name', 'percentage', 'from_date', 'to_date'],
        search_fields={
            'name': 'name'
        },
        add=True,
        edit=True,
        delete=True,
        related_model=Product,
        related_field_name='discounts',  # many-to-many reverse accessor
        related_title='Discounted Products',
        related_fields={
            'name': 'Product Name',
            'category': 'Category',
            'manufacturer': 'Manufacturer',
            'sale_price': 'Sale Price (€)',
        }
    )

def add_discount(request):
    return add_object(
        request=request,
        form_class=DiscountForm,
        model=Discount,
        success_url='discount_list'
    )

def edit_discount(request, discount_id):
    return edit_object(
        request=request,
        form_class=DiscountForm,
        model=Discount,
        object_id=discount_id,
        success_url='discount_list'
    )

@require_POST
def delete_discount(request, discount_id):
    if delete_object(request, Discount, discount_id):
        return redirect('discount_list')
    return redirect('discount_list')

# Public Product List
def public_product_list(request):
    products = Product.objects.select_related("category", "manufacturer").all()
    data = [
        {
            "name": p.name,
            "category": p.category.name,
            "manufacturer": p.manufacturer.name,
            "price": str(p.sale_price),
            "description": p.description,
        }
        for p in products
    ]
    return JsonResponse(data, safe=False)
