# home/views.py
from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.models import User
from django.contrib.auth.decorators import login_required
from django.core.paginator import Paginator
import json
from django.http import JsonResponse
from django.forms import modelformset_factory
from django.utils import timezone
from .models import Manufacturer, ActivityLog, Category, Product, Inventory, PurchaseTransaction, PurchasedProduct, Customer, SaleTransaction, SoldProduct
from .forms import UserCreationForm, UserEditForm, ManufacturerForm, CategoryForm, ProductForm, PurchaseTransactionForm, PurchasedProductForm, CustomerForm, SaleTransactionForm, SoldProductForm, DateRangeForm
from .utils import *
from django.contrib import messages
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_POST
from django.utils.dateparse import parse_date
from django.utils.timezone import now
from datetime import date, timedelta
from django.db import transaction  # for atomic operations
from django.db.models import Sum

# Homepage
def homepage(request):
    today = date.today()

    inventory = Inventory.objects.select_related('product').order_by('expiry_date')

    # Add days_diff to each item in inventory
    for item in inventory:
        days_until_expiry = (item.expiry_date - today).days  # Calculate days difference
        item.days_diff = days_until_expiry  # Add it to the item object

    return render(request, 'index.html', {
        'inventory': inventory,
        'today': today,
    })

# Activity Log
def activity_log_list(request):
    return list_objects(
        request,
        model=ActivityLog,
        columns=['timestamp', 'user', 'action', 'additional_info'],
        search_fields={'user': 'user__username', 'action': 'action', 'additional_info': 'additional_info'}
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
        sort_fields=['date_joined', 'last_login'],
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
        search_fields={'name': 'name', 'address': 'address'},
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

def delete_manufacturer(request, manufacturer_id):
    if delete_object(request, Manufacturer, manufacturer_id):
        return redirect('manufacturer_list')
    return redirect('manufacturer_list')  # In case of error, just redirect

# Category management
def category_list(request):
    return list_objects(
        request,
        model=Category,
        columns=['name', 'description', 'requires_prescription'],
        search_fields={'category_name': 'name'},
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

def delete_category(request, category_id):
    if delete_object(request, Product, category_id):
        return redirect('category_list')
    return redirect('category_list')  # In case of error, just redirect

# Product management
def product_list(request):
    return list_objects(
        request,
        model=Product,
        columns=['name', 'category', 'manufacturer', 'sale_price'],
        search_fields={'product_name': 'name', 'manufacturer_name': 'manufacturer__name'},
        add=True,
        actions=True
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

def delete_product(request, product_id):
    if delete_object(request, Product, product_id):
        return redirect('product_list')
    return redirect('product_list')  # In case of error, just redirect

# Inventory management
def inventory_list(request):
    # Get search parameters from the GET request
    product_name_query = request.GET.get('product_name', '')
    manufacturer_name_query = request.GET.get('manufacturer_name', '')
    sort_by = request.GET.get('sort_by', '-updated_at')  # Default sort by 'updated_at'
    
    # Filter inventory items based on search parameters
    inventory_items = Inventory.objects.select_related('product__manufacturer').all()

    if product_name_query:
        inventory_items = inventory_items.filter(product__name__icontains=product_name_query)
    if manufacturer_name_query:
        inventory_items = inventory_items.filter(product__manufacturer__name__icontains=manufacturer_name_query)
    
    # Sort inventory items by the specified field
    if sort_by in ['updated_at', 'expiry_date']:
        inventory_items = inventory_items.order_by(sort_by if sort_by == 'expiry_date' else f'-{sort_by}')

    paginator = Paginator(inventory_items, 10)  # Show 10 items per page
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    # Preserve query parameters (except for 'page')
    query_params = request.GET.copy()
    if 'page' in query_params:
        query_params.pop('page')
    query_string = query_params.urlencode()
        
    return render(request, 'inventory_list.html', {
        'inventory_items': page_obj,
        'page_obj': page_obj,
        'product_name_query': product_name_query,
        'manufacturer_name_query': manufacturer_name_query,
        'sort_by': sort_by,
        'query_string': query_string,
    })

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

    paginator = Paginator(purchase_transactions, 10)  # Show 10 items per page
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    # Preserve query parameters (except for 'page')
    query_params = request.GET.copy()
    if 'page' in query_params:
        query_params.pop('page')
    query_string = query_params.urlencode()

    return render(request, 'purchase_transaction_list.html', {
        'purchase_transactions': page_obj,
        'page_obj': page_obj,
        'invoice_number_query': invoice_number_query,
        'manufacturer_name_query': manufacturer_name_query,
        'query_string': query_string,
    })

def add_purchase_transaction(request):
    PurchasedProductFormSet = modelformset_factory(
        PurchasedProduct, form=PurchasedProductForm, extra=1, can_delete=True
    )

    if request.method == "POST":
        form = PurchaseTransactionForm(request.POST)
        formset = PurchasedProductFormSet(request.POST, prefix="products")

        if form.is_valid() and formset.is_valid():
            purchase_transaction = form.save(commit=False)
            purchase_transaction.purchase_date = timezone.localtime(timezone.now())  
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
                    
            return redirect('purchase_transaction_list')
        else:
            # Set correct queryset for product fields in formset
            for subform in formset:
                if 'manufacturer' in request.POST:
                    try:
                        manufacturer_id = int(request.POST.get("manufacturer"))
                        subform.fields['product'].queryset = Product.objects.filter(manufacturer_id=manufacturer_id)
                    except (ValueError, TypeError):
                        subform.fields['product'].queryset = Product.objects.none()

            return render(request, "add_purchase_transaction.html", {
                "form": form,
                "formset": formset,
                "manufacturers": Manufacturer.objects.all(),
                "errors": form.errors,
                "formset_errors": formset.errors,
            })

    else:
        form = PurchaseTransactionForm()
        formset = PurchasedProductFormSet(queryset=PurchasedProduct.objects.none(), prefix="products")

    return render(request, "add_purchase_transaction.html", {
        "form": form,
        "formset": formset,
        "manufacturers": Manufacturer.objects.all(),
        "errors": form.errors,
        "formset_errors": formset.errors,
    })

def get_products_by_manufacturer(request):
    manufacturer_id = request.GET.get('manufacturer_id')
    if manufacturer_id:
        products = Product.objects.filter(manufacturer_id=manufacturer_id)
        product_data = list(products.values('id', 'name'))
        return JsonResponse(product_data, safe=False)
    return JsonResponse({'error': 'No manufacturer selected'}, status=400)

@csrf_exempt
@require_POST
def scan_purchase_transaction(request):
    try:
        data = json.loads(request.body)

        # Validate JSON structure
        required_fields = {"invoice_number", "manufacturer", "purchase_date", "total_cost", "products"}
        if not required_fields.issubset(data.keys()):
            return JsonResponse({"success": False, "message": "Missing required fields."})

        # Find manufacturer
        try:
            manufacturer = Manufacturer.objects.get(name=data["manufacturer"])
        except Manufacturer.DoesNotExist:
            return JsonResponse({"success": False, "message": "Manufacturer not found."})

        # Create transaction
        transaction = PurchaseTransaction.objects.create(
            invoice_number=data["invoice_number"],
            manufacturer=manufacturer,
            purchase_date=parse_date(data["purchase_date"]) or now(),
            total_cost=data["total_cost"],
            remarks=data.get("remarks", "")
        )

        # Add products
        for item in data["products"]:
            try:
                product = Product.objects.get(name=item["product"], manufacturer=manufacturer)
            except Product.DoesNotExist:
                transaction.delete()
                return JsonResponse({"success": False, "message": f"Product not found: {item['product']}"})

            PurchasedProduct.objects.create(
                purchase_transaction=transaction,
                product=product,
                batch_number=item.get("batch_number", ""),
                quantity=item["quantity"],
                purchase_price=item["purchase_price"],
                expiry_date=parse_date(item["expiry_date"])
            )

        # Update inventory after saving all purchased products
        for purchased_product in transaction.purchased_products.all():
            inventory_item, created = Inventory.objects.get_or_create(
                product=purchased_product.product,
                expiry_date=purchased_product.expiry_date,
                defaults={'quantity': purchased_product.quantity}
            )
            if not created:
                inventory_item.quantity += purchased_product.quantity
                inventory_item.save()

        if request.user.is_authenticated:
            log_activity(
                user=request.user,
                action="scanned purchase transaction",
                additional_info=f"Invoice #{transaction.invoice_number}, Manufacturer: {manufacturer.name}"
            )

        return JsonResponse({"success": True})
    
    except Exception as e:
        return JsonResponse({"success": False, "message": str(e)})

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

    messages.success(request, "Purchase transaction deleted and inventory updated.")
    return redirect('purchase_transaction_list')

# Customer management
def customer_list(request):
    return list_objects(
        request,
        model=Customer,
        columns=['full_name', 'birthdate', 'phone_number', 'email', 'address'],
        search_fields={'name': 'full_name'},
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

    paginator = Paginator(sale_transactions, 10)  # Show 10 items per page
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    # Preserve query parameters (except for 'page')
    query_params = request.GET.copy()
    if 'page' in query_params:
        query_params.pop('page')
    query_string = query_params.urlencode()

    return render(request, 'sale_transaction_list.html', {
        'sale_transactions': page_obj,
        'page_obj': page_obj,
        'transaction_number_query': transaction_number_query,
        'customer_name_query': customer_name_query,
        'query_string': query_string,
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

                    messages.success(request, "Sale transaction successfully recorded.")
                    return redirect('sale_transaction_list')

            except Exception as e:
                messages.error(request, f"Error saving transaction: {e}")
                return render(request, "add_sale_transaction.html", {
                    "form": form,
                    "formset": formset,
                    "customers": Customer.objects.all(),
                    "inventory_items": Inventory.objects.select_related('product', 'product__manufacturer').all(),
                    "errors": form.errors,
                    "formset_errors": formset.errors,
                })

        return render(request, "add_sale_transaction.html", {
            "form": form,
            "formset": formset,
            "customers": Customer.objects.all(),
            "inventory_items": Inventory.objects.select_related('product', 'product__manufacturer').all(),
            "errors": form.errors,
            "formset_errors": formset.errors,
        })

    else:
        form = SaleTransactionForm()
        formset = SoldProductFormSet(queryset=SoldProduct.objects.none(), prefix="products")

    return render(request, "add_sale_transaction.html", {
        "form": form,
        "formset": formset,
        "customers": Customer.objects.all(),
        "inventory_items": Inventory.objects.select_related('product', 'product__manufacturer').all(),
        "errors": form.errors,
        "formset_errors": formset.errors,
    })

def get_inventory_price(request, inventory_id):
    try:
        inventory = Inventory.objects.get(id=inventory_id)
        price = inventory.product.sale_price
        return JsonResponse({'price': float(price)})
    except Inventory.DoesNotExist:
        return JsonResponse({'error': 'Not found'}, status=404)

@csrf_exempt
@require_POST
def scan_sale_transaction(request):
    try:
        data = json.loads(request.body)

        required_fields = {"transaction_number", "transaction_date", "price", "discount", "cash_received", "payment_method", "products"}
        if not required_fields.issubset(data.keys()):
            return JsonResponse({"success": False, "message": "Missing required fields."})

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

        # Create transaction
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

        # Add sold products
        for item in data["products"]:
            inventory = Inventory.objects.get(id=item["inventory_id"])
            if inventory.quantity < item["quantity"]:
                transaction.delete()
                return JsonResponse({"success": False, "message": f"Not enough stock for {inventory.product.name}."})

            SoldProduct.objects.create(
                sale_transaction=transaction,
                inventory_item=inventory,
                quantity=item["quantity"],
                sale_price=item.get("sale_price", inventory.product.sale_price)
            )

            inventory.quantity -= item["quantity"]
            inventory.save()

        if request.user.is_authenticated:
            log_activity(
                user=request.user,
                action="scanned sale transaction",
                additional_info=f"Transaction #{transaction.transaction_number}"
            )

        return JsonResponse({"success": True})

    except Inventory.DoesNotExist:
        return JsonResponse({"success": False, "message": "Inventory item not found."})
    except Exception as e:
        return JsonResponse({"success": False, "message": str(e)})

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

    messages.success(request, "Sale transaction deleted and inventory updated.")
    return redirect('sale_transaction_list')

def financial_summary(request):
    total_purchase = 0
    total_sales = 0
    profit = 0
    form = DateRangeForm(request.GET or None)

    if form.is_valid():
        from_date = form.cleaned_data['from_date']
        to_date = form.cleaned_data['to_date']

        purchases = PurchaseTransaction.objects.filter(purchase_date__date__range=(from_date, to_date))
        sales = SaleTransaction.objects.filter(transaction_date__date__range=(from_date, to_date))

        total_purchase = purchases.aggregate(Sum('total_cost'))['total_cost__sum'] or 0
        total_sales = sales.aggregate(Sum('price'))['price__sum'] or 0
        profit = total_sales - total_purchase

    context = {
        'form': form,
        'total_purchase': total_purchase,
        'total_sales': total_sales,
        'profit': profit,
    }
    return render(request, 'financial_summary.html', context)