# home/utils.py
import datetime
from urllib.parse import urlencode
import logging

from django.shortcuts import render, redirect, get_object_or_404
from django.db import IntegrityError
from django.contrib import messages
from django.core.paginator import Paginator
from django.core.exceptions import FieldDoesNotExist
from django.urls import reverse, NoReverseMatch
from django.utils.dateparse import parse_date
from django.utils import timezone
from django.utils.timezone import localtime
from django.utils.translation import gettext, gettext_lazy as _
from django.utils.text import capfirst, slugify

from .models import ActivityLog

logger = logging.getLogger(__name__)

def log_activity(user, action, additional_info=""):
    """
    Logs an activity for a specific user.

    :param user: The user who performed the action
    :param action: A brief description of the action
    :param additional_info: Optional additional details about the action
    """
    ActivityLog.objects.create(
        user=user,
        action=action,
        additional_info=additional_info
    )

def get_object_name(obj):
    try:
        return getattr(obj, 'name', None) or str(obj)
    except Exception:
        return str(obj)  # Safe fallback

def delete_object(request, model, object_id):
    """
    Generic view to handle the deletion of an existing object.
    
    :param request: The HTTP request object.
    :param model: The model class (e.g., User, Manufacturer, Product).
    :param object_id: The ID of the object to delete.
    """
    model_name = model._meta.verbose_name
    object_name = None
    try:
        obj = model.objects.get(id=object_id)  # Get the object by ID
        object_name = get_object_name(obj)

        obj.delete()  # Delete the object
        # Log the activity
        log_activity(
            user=request.user,
            action=f"deleted {model_name} {object_name}",
            additional_info=f"{model_name} ID: {object_id}"
        )
        
        messages.success(request, f"The {model_name} '{object_name}' deleted.")
        return True  # Return success flag

    except model.DoesNotExist:
        messages.error(request, f"The {model_name} '{object_name}' does not exist.")
        return False

    except IntegrityError:
        messages.error(request, f"Cannot delete {model_name} '{object_name}' because it is referenced by other record(s).")
        return False

    except Exception as e:
        logger.error(f"Error occurred while deleting {model_name} '{object_name}': {str(e)}")
        messages.error(request, "An unexpected error occurred while trying to delete the item. Please try again later.")
        return False

def add_object(request, form_class, model, success_url):
    """
    Generic view to handle the addition of a new object.

    :param request: HTTP request
    :param form_class: The form class to be used
    :param model: The model class (e.g., User, Manufacturer, Product)
    :param success_url: The URL to redirect to after success (e.g., 'user_list')
    """
    model_name = model._meta.verbose_name
    if request.method == 'POST':
        form = form_class(request.POST)
        if form.is_valid():
            instance = form.save()  # Save the new object
            object_name = get_object_name(instance)

            # Log the activity
            log_activity(
                user=request.user,
                action=f"added new {model_name} {object_name}",
                additional_info=f"{model_name} ID: {instance.id}"
            )

            messages.success(request, f"The {model_name} '{object_name}' added.")
            return redirect(success_url)  # Redirect to the success URL
    else:
        form = form_class()  # Empty form on GET request

    try:
        resolved_success_url = reverse(success_url)
    except NoReverseMatch:
        resolved_success_url = success_url

    title = _('Add New %(model)s') % {'model': model_name.capitalize()}

    return render(request, 'form_page.html', {
        'title': title,  # Dynamic title
        'form_title': f'{model_name.capitalize()} Details',  # Dynamic form legend/title
        'form': form,  # Form passed to template
        'success_url': resolved_success_url,
    })

def edit_object(request, form_class, model, object_id, success_url):
    """
    Generic view to handle the editing of an existing object.

    :param request: HTTP request
    :param form_class: The form class to be used
    :param model: The model class (e.g., User, Manufacturer, Product)
    :param object_id: The ID of the object to edit
    :param success_url: The URL to redirect to after success (e.g., 'user_list')
    """
    model_name = model._meta.verbose_name
    obj = get_object_or_404(model, id=object_id)  # Fetch the object by ID
    object_name = get_object_name(obj)

    if request.method == 'POST':
        form = form_class(request.POST, instance=obj)  # Bind the form with the existing object
        if form.is_valid():
            form.save()  # Save the updated object
            # Log the activity
            log_activity(
                user=request.user,
                action=f"edited {model_name} {object_name}",
                additional_info=f"{model_name} ID: {object_id}"
            )
            messages.success(request, f"The {model_name} '{object_name}' updated.")
            return redirect(success_url)  # Redirect to the success URL after saving
    else:
        form = form_class(instance=obj)  # Prepopulate the form with the object's current data

    try:
        resolved_success_url = reverse(success_url)
    except NoReverseMatch:
        resolved_success_url = success_url

    title = _('Edit %(model)s') % {'model': model_name.capitalize()}

    return render(request, 'form_page.html', {
        'title': title,  # Dynamic title
        'form_title': f'{model_name.capitalize()} Details',  # Dynamic form legend/title
        'form': form,  # Form passed to template
        'success_url': resolved_success_url,
    })

def list_objects(request, model, columns=None, search_fields=None, sort_fields=None, extra_context=None, add=False, edit=False, delete=False, 
                 related_model=None, related_field_name=None, related_title=None, related_fields=None, model_url=None):
    """
    Generic function to display a paginated and searchable list of objects.

    :param request: HTTP request object.
    :param model: The model class (e.g., User, Manufacturer, Product).
    :param columns: Column names, can be either a list or a dictionary. Use dictionary values for alternative names.
    :param search_fields: A dictionary where keys are request GET parameters and values are model fields to filter by.
    :param sort_field: Sort option names, can be either a list or a dictionary. Use dictionary values for alternative names.
    :param extra_context: Any additional context data needed in the template.
    :param add: Whether to include Add button in the template.
    :param edit: Whether to include Edit button in the template.
    :param delete: Whether to include Delete button in the template.
    """
    # Use the pre-fetched object_list if provided
    objects = extra_context.get('object_list') if extra_context and 'object_list' in extra_context else model.objects.all()

    # Columns configuration
    if isinstance(columns, dict):
        column_keys = list(columns.keys())
        column_labels = {
            key: gettext(value) for key, value in columns.items()
        }
    else:
        column_keys = columns or []
        column_labels = {
            col: translate_field(model, col)
            for col in column_keys
        }

    # Search configuration
    search_values = {}
    if search_fields:
        for param, field in search_fields.items():
            value = request.GET.get(param, '').strip()
            if value:
                objects = objects.filter(**{f"{field}__icontains": value})
            search_values[param] = value  # Preserve search values

    search_labels = {}
    if search_fields:
        for param, field in search_fields.items():
            try:
                base_field = field.split('__')[0]
                model_field = model._meta.get_field(base_field)
                search_labels[param] = str(model_field.verbose_name).title()
            except FieldDoesNotExist:
                search_labels[param] = param.replace('_', ' ').title()


    # Sort configuration
    sort_by = request.GET.get('sort_by', '')
    if isinstance(sort_fields, dict):
        valid_sort_fields = list(sort_fields.keys())
    else:
        valid_sort_fields = sort_fields or []

    if sort_by in valid_sort_fields:
        objects = objects.order_by(sort_by)
    else:
        # Apply default ordering only if no valid sort_by given
        default_ordering = getattr(model._meta, "ordering", None) or ["id"]
        objects = objects.order_by(*default_ordering)

    page_obj, query_string = paginate_with_query_params(request, objects)

    # Data provided to the template
    context = {
        'title': extra_context.get('title', gettext(model._meta.verbose_name).title()) if extra_context else gettext(model._meta.verbose_name).title(),
        'model_verbose_name': gettext(model._meta.verbose_name).title(),
        'model_name': model._meta.model_name,
        'model_url': slugify(model_url if model_url else model._meta.model_name),  # produces lowercase, hyphenated name, e.g. 'purchase-transaction'
        'page_obj': page_obj,
        'columns': column_keys,
        'column_labels': column_labels,
        'search_queries': search_values,
        'search_labels': search_labels, # Translatable search labels
        'sort_queries': sort_fields,
        'sort_by': sort_by,
        'add': add, # Show Add button
        'edit': edit,  # Show Edit button
        'delete': delete,  # Show Delete button
        'action': edit or delete, # Hides actions column if none of the buttons in the column are enabled
        'query_string': query_string,  # Pass the query string for pagination links
        'related_title': related_title or (gettext(related_model._meta.verbose_name_plural).title() if related_model else None),
        'related_model_name': related_model._meta.model_name if related_model else None,
        'related_field_name': related_field_name,
        'related_fields': related_fields,
        'scan_view_name': f"scan_{model._meta.model_name}",
    }

    # Merge extra context if provided
    if extra_context:
        context.update(extra_context)

    return render(request, 'list_page.html', context)

def paginate_with_query_params(request, queryset, per_page=10, page_param='page'):
    paginator = Paginator(queryset, per_page)
    page_number = request.GET.get(page_param)
    page_obj = paginator.get_page(page_number)

    querydict = request.GET.copy()
    for key in ['page', 'lowstockpage']:
        querydict.pop(key, None)

    query_string = urlencode(querydict)

    return page_obj, query_string

def make_aware_datetime(date_str):
    # Parse date string to date
    date_obj = parse_date(date_str)
    if not date_obj:
        return timezone.now()
    # Convert date to datetime at midnight
    dt = datetime.datetime.combine(date_obj, datetime.time.min)
    # Make it timezone-aware (using current timezone)
    aware_dt = timezone.make_aware(dt, timezone.get_current_timezone())
    return aware_dt

def format_value(value):
    print("DEBUG format_value:", value, type(value))
    if isinstance(value, datetime.datetime):
        dt = localtime(value)
        time_str = dt.strftime('%I:%M %p').lstrip('0').lower()
        time_str = time_str.replace('am', 'a.m.').replace('pm', 'p.m.')
        return dt.strftime('%d %b %Y') + ', ' + time_str
    elif isinstance(value, datetime.date):
        return value.strftime('%d %b %Y')
    return str(value)

def get_generic_field_translation(field_name):
    translations = {
        'stock': _('Stock'),
        'quantity': _('Quantity'),
        'expiry_date': _('Expiry Date'),
        'sale_price': _('Sale Price'),
        'created_at': _('Created At'),
        'updated_at': _('Updated At'),
        'manufacturer': _('Manufacturer'),
        'category': _('Category'),
        'address': _('Address'),
        'phone_number': _('Phone Number'),
        'full_name': _('Full Name'),
        'birthdate': _('Birthdate'),
        'transactions': _('Transactions'),
        'description': _('Description'),
        'requires_prescription': _('Requires Prescription'),
        'low_stock_threshold': _('Low Stock Threshold'),
        'product': _('Product'),
        'invoice_number': _('Invoice #'),
        'purchase_date': _('Purchase Date'),
        'total_cost': _('Total Cost'),
        'transaction_number': _('Transaction #'),
        'customer': _('Customer'),
        'transaction_date': _('Date'),
        'price': _('Price'),
        'discount': _('Discount'),
        'total': _('Total'),
        'cash_received': _('Cash'),
        'payment_method': _('Payment Method'),
        'percentage': _('Percentage'),
        'from_date': _('From Date'),
        'to_date': _('To Date'),
        'timestamp': _('Timestamp'),
        'user': _('User'),
        'action': _('Action'),
        'additional_info': _('Additional Info'),
    }
    return translations.get(field_name, None)

def translate_field(model, field_name):
    label = get_generic_field_translation(field_name)
    if label:
        return label

    try:
        return capfirst(model._meta.get_field(field_name).verbose_name)
    except Exception:
        return _(field_name.replace('_', ' ').capitalize())
