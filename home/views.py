# home/views.py
import json
from datetime import date, timedelta
from reportlab.pdfgen import canvas
from io import BytesIO
from collections import defaultdict
import logging

logger = logging.getLogger(__name__)

from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.models import User
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_POST
from django.utils.dateparse import parse_date
from django.utils.timezone import now
from django.utils import timezone
from django.db import transaction, IntegrityError
from django.db.models import Sum, F, Value, ExpressionWrapper, DecimalField, ForeignKey, DateTimeField, DateField
from django.db.models.functions import Coalesce
from django.http import JsonResponse, HttpResponse
from django.forms import modelformset_factory
from django.forms.models import model_to_dict
from django.contrib import messages
from django.urls import reverse
from django.apps import apps

from .models import (
    ActivityLog, Customer, 
    Manufacturer, Category, Product, Inventory, 
    PurchaseTransaction, PurchasedProduct, SaleTransaction, SoldProduct
)
from .forms import (
    UserCreationForm, UserEditForm, CustomerForm, DateRangeForm,
    ManufacturerForm, CategoryForm, ProductForm, 
    PurchaseTransactionForm, PurchasedProductForm, PurchaseScanForm,
    SaleTransactionForm, SoldProductForm, SaleScanForm
)
from .utils import paginate_with_query_params, add_object, edit_object, delete_object, list_objects, log_activity, make_aware_datetime

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
        actions=True
    )

def add_user(request):
    return add_object(
        request=request,
        form_class=UserCreationForm,
        model=User,
        success_url='user_list'
    )

def edit_user(request, user_id):
    return edit_object(
        request=request,
        form_class=UserEditForm,
        model=User,
        object_id=user_id,
        success_url='user_list'
    )

@require_POST
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
        actions=True
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
        actions=True
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
        actions=True,
        extra_context={'object_list': products_with_stock}
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
        }
    )

# Purchase Transactions management
def purchase_transaction_list(request):
    # Get search parameters from the GET request
    invoice_number_query = request.GET.get('invoice_number', '').strip()
    manufacturer_name_query = request.GET.get('manufacturer_name', '').strip()
    
    # Filter purchase transactions based on search parameters
    # purchase_transactions = PurchaseTransaction.objects.all()
    purchase_transactions = PurchaseTransaction.objects.prefetch_related('purchased_products').all()

    if invoice_number_query:
        purchase_transactions = purchase_transactions.filter(invoice_number__icontains=invoice_number_query)
    if manufacturer_name_query:
        purchase_transactions = purchase_transactions.filter(manufacturer__name__icontains=manufacturer_name_query)
    
    # Sort transactions by purchase date (or other fields as needed)
    purchase_transactions = purchase_transactions.order_by('-purchase_date')

    # Scan via Django Form because it handles errors, such as scan the same file multiple time, better than Javascript
    scan_form = PurchaseScanForm()

    page_obj, query_string = paginate_with_query_params(request, purchase_transactions)

    return render(request, 'purchase_transaction_list.html', {
        'purchase_transactions': page_obj,
        'page_obj': page_obj,
        'invoice_number_query': invoice_number_query,
        'manufacturer_name_query': manufacturer_name_query,
        'query_string': query_string,
        'scan_form': scan_form
    })

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
                remarks=data.get("remarks", "")
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
            messages.error(request, f"Cannot delete: Not enough inventory for {purchased_product.product.name}.")
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
    return list_objects(
        request,
        model=Customer,
        columns=['full_name', 'birthdate', 'phone_number', 'email', 'address'],
        search_fields={
            'name': 'full_name'
        },
        add=True,
        actions=True
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
    transaction_number_query = request.GET.get('transaction_number', '').strip()
    customer_name_query = request.GET.get('customer_name', '').strip()

    sale_transactions = SaleTransaction.objects.prefetch_related('sold_products').all()

    if transaction_number_query:
        sale_transactions = sale_transactions.filter(transaction_number__icontains=transaction_number_query)
    if customer_name_query:
        sale_transactions = sale_transactions.filter(customer__full_name__icontains=customer_name_query)

    sale_transactions = sale_transactions.order_by('-transaction_date')

    # Scan via Django Form because it handles errors, such as scan the same file multiple time, better than Javascript
    scan_form = SaleScanForm()

    page_obj, query_string = paginate_with_query_params(request, sale_transactions)

    return render(request, 'sale_transaction_list.html', {
        'sale_transactions': page_obj,
        'page_obj': page_obj,
        'transaction_number_query': transaction_number_query,
        'customer_name_query': customer_name_query,
        'query_string': query_string,
        'scan_form': scan_form
    })

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
                    sale_transaction.created_by = request.user
                    sale_transaction.price = 0  # will be calculated below
                    sale_transaction.save()

                    # Handle sold products
                    for sold_form in formset:
                        if sold_form.cleaned_data and not sold_form.cleaned_data.get('DELETE', False):
                            sold_product = sold_form.save(commit=False)
                            sold_product.sale_transaction = sale_transaction
                            sold_product.sale_price = sold_product.inventory_item.product.sale_price
                            sold_product.save()

                            # Calculate total price
                            sale_transaction.price += sold_product.total_price or 0

                            # Subtract quantity from Inventory
                            inventory_qs = sold_product.inventory_item

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
                transaction_date=parse_date(data["transaction_date"]) or now(),
                price=data["price"],
                discount=data["discount"],
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

def financial_summary(request):
    total_purchase = 0
    total_sales = 0
    profit = 0
    form = DateRangeForm(request.GET or None)

    product_summary = []

    if form.is_valid():
        from_date = form.cleaned_data['from_date']
        to_date = form.cleaned_data['to_date']

        purchases = PurchaseTransaction.objects.filter(purchase_date__date__range=(from_date, to_date))
        sales = SaleTransaction.objects.filter(transaction_date__date__range=(from_date, to_date))

        total_purchase = purchases.aggregate(Sum('total_cost'))['total_cost__sum'] or 0
        total_sales = sales.aggregate(Sum('price'))['price__sum'] or 0
        profit = total_sales - total_purchase

        product_summary = defaultdict(lambda: {
            'purchased_quantity': 0,
            'total_spent': 0,
            'sold_quantity': 0,
            'total_earned': 0
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

    context = {
        'form': form,
        'total_purchase': total_purchase,
        'total_sales': total_sales,
        'profit': profit,
        'product_summary': product_summary,
    }
    return render(request, 'financial_summary.html', context)

def export_financial_summary_pdf(request):
    form = DateRangeForm(request.GET or None)

    if not form.is_valid():
        print("[DEBUG] Export PDF form is invalid.")
        print("[DEBUG] GET data:", request.GET.dict())
        print("[DEBUG] Form errors:", form.errors.as_json())
        return redirect('financial_summary')

    from_date = form.cleaned_data['from_date']
    to_date = form.cleaned_data['to_date']

    purchases = PurchaseTransaction.objects.filter(purchase_date__date__range=(from_date, to_date))
    sales = SaleTransaction.objects.filter(transaction_date__date__range=(from_date, to_date))

    total_purchase = purchases.aggregate(Sum('total_cost'))['total_cost__sum'] or 0
    total_sales = sales.aggregate(Sum('price'))['price__sum'] or 0
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
    p.setFont("Helvetica-Bold", 14)
    p.drawString(100, 800, "Financial Summary Report")
    p.setFont("Helvetica", 12)

    p.drawString(100, 770, f"Date Range: {from_date.strftime('%B %d, %Y')} to {to_date.strftime('%B %d, %Y')}")
    p.drawString(100, 750, f"Total Purchase Cost: € {total_purchase:,.2f}")
    p.drawString(100, 730, f"Total Sales Revenue: € {total_sales:,.2f}")
    p.drawString(100, 710, f"Estimated Profit: € {profit:,.2f}")

    # Product summary table
    y = 680
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

        # Name left-aligned, numbers centered in their columns
        p.drawString(x_name, y, str(item['name'])[:32])
        p.drawCentredString(x_bought + col_width // 2, y, str(item['purchased_quantity']))
        p.drawCentredString(x_sold + col_width // 2, y, str(item['sold_quantity']))
        p.drawCentredString(x_spent + col_width // 2, y, f"{item['total_spent']:,.2f}")
        p.drawCentredString(x_earned + col_width // 2, y, f"{item['total_earned']:,.2f}")
        p.drawCentredString(x_profit + col_width // 2, y, f"{item['profit']:,.2f}")
        y -= 15

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
        # Special case: if user model requested, get it from auth app
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

            # Format value based on field type
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

            # Format field label
            label = field.verbose_name.title()
            if label == "Id":
                label = "ID"

            data[label] = display_value

        return JsonResponse(data)
    
    except model.DoesNotExist:
        return JsonResponse({'error': 'Object not found'}, status=404)
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)