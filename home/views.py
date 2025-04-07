# home/views.py
from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.models import User
from django.contrib.auth.decorators import login_required
from django.core.paginator import Paginator
import json
from django.http import JsonResponse
from django.forms import modelformset_factory
from django.utils import timezone
from .models import Manufacturer, ActivityLog, Category, Product, Inventory, PurchaseTransaction, PurchasedProduct
from .forms import UserCreationForm, UserEditForm, ManufacturerForm, CategoryForm, ProductForm, PurchaseTransactionForm, PurchasedProductForm
from .utils import delete_object, add_object, edit_object, list_objects
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_POST
from django.utils.dateparse import parse_date
from django.utils.timezone import now

# Homepage
def homepage(request):
    return render(request, 'index.html')

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

    return render(request, 'inventory_list.html', {
        'inventory_items': inventory_items,
        'product_name_query': product_name_query,
        'manufacturer_name_query': manufacturer_name_query,
        'sort_by': sort_by,
    })

# Purchase Transactions management
def purchase_transaction_list(request):
    # Get search parameters from the GET request
    invoice_number_query = request.GET.get('invoice_number', '').strip()
    manufacturer_name_query = request.GET.get('manufacturer_name', '').strip()
    
    # Filter purchase transactions based on search parameters
    purchase_transactions = PurchaseTransaction.objects.all()

    if invoice_number_query:
        purchase_transactions = purchase_transactions.filter(invoice_number__icontains=invoice_number_query)
    if manufacturer_name_query:
        purchase_transactions = purchase_transactions.filter(manufacturer__name__icontains=manufacturer_name_query)
    
    # Sort transactions by purchase date (or other fields as needed)
    purchase_transactions = purchase_transactions.order_by('-purchase_date')

    return render(request, 'purchase_transaction_list.html', {
        'purchase_transactions': purchase_transactions,
        'invoice_number_query': invoice_number_query,
        'manufacturer_name_query': manufacturer_name_query,
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

        return JsonResponse({"success": True})
    
    except Exception as e:
        return JsonResponse({"success": False, "message": str(e)})

