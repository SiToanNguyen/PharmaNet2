# home/utils.py
from django.shortcuts import render, redirect, get_object_or_404
from django.db import IntegrityError
from django.contrib import messages
from .models import ActivityLog
from django.core.paginator import Paginator

import logging
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

def delete_object(request, model, object_id):
    """
    Generic view to handle the deletion of an existing object.
    
    :param request: The HTTP request object.
    :param model: The model class (e.g., User, Manufacturer, Product).
    :param object_id: The ID of the object to delete.
    :return: Boolean indicating success or failure.
    """
    model_name = model._meta.verbose_name
    try:
        obj = model.objects.get(id=object_id)  # Get the object by ID
        object_name = str(obj)  # Use the model's string representation (e.g., name, username, etc.)

        obj.delete()  # Delete the object
        # Log the activity
        log_activity(
            user=request.user,
            action=f"deleted {model_name} {object_name}",
            additional_info=f"{model_name} ID: {object_id}"
        )
        
        messages.success(request, f"The {model_name} '{object_name}' has been deleted.")
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
    :return: Rendered response with form or redirection after success
    """
    model_name = model._meta.verbose_name
    if request.method == 'POST':
        form = form_class(request.POST)
        if form.is_valid():
            instance = form.save()  # Save the new object
            object_name = instance.name if hasattr(instance, 'name') else str(instance)  # Use name or str of the instance

            # Log the activity
            log_activity(
                user=request.user,
                action=f"added new {model_name} {object_name}",
                additional_info=f"{model_name} ID: {instance.id}"
            )

            messages.success(request, f"The {model_name} '{object_name}' has been added.")
            return redirect(success_url)  # Redirect to the success URL

    else:
        form = form_class()  # Empty form on GET request

    return render(request, 'form_page.html', {
        'title': f'Add New {model_name.capitalize()}',  # Dynamic title
        'form_title': f'{model_name.capitalize()} Details',  # Dynamic form legend/title
        'form': form,  # Form passed to template
    })

def edit_object(request, form_class, model, object_id, success_url):
    """
    Generic view to handle the editing of an existing object.

    :param request: HTTP request
    :param form_class: The form class to be used
    :param model: The model class (e.g., User, Manufacturer, Product)
    :param object_id: The ID of the object to edit
    :param success_url: The URL to redirect to after success (e.g., 'user_list')
    :return: Rendered response with form or redirection after success
    """
    model_name = model._meta.verbose_name
    obj = get_object_or_404(model, id=object_id)  # Fetch the object by ID
    object_name = str(obj)  # Use the model's string representation (e.g., name, username, etc.)

    if request.method == 'POST':
        form = form_class(request.POST, instance=obj)  # Bind the form with the existing object
        if form.is_valid():
            instance = form.save()  # Save the updated object
            # Log the activity
            log_activity(
                user=request.user,
                action=f"edited {model_name} {object_name}",
                additional_info=f"{model_name} ID: {object_id}"
            )
            messages.success(request, f"The {model_name} '{object_name}' has been updated.")
            return redirect(success_url)  # Redirect to the success URL after saving
    else:
        form = form_class(instance=obj)  # Prepopulate the form with the object's current data

    return render(request, 'form_page.html', {
        'title': f'Edit {model_name.capitalize()}',  # Dynamic title
        'form_title': f'{model_name.capitalize()} Details',  # Dynamic form legend/title
        'form': form,  # Form passed to template
    })

def list_objects(request, model, columns=None, search_fields=None, sort_fields=None, extra_context=None, add=False, actions=False):
    """
    Generic function to display a paginated and searchable list of objects.

    :param request: HTTP request object.
    :param model: The model class (e.g., User, Manufacturer, Product).
    :param template_name: The template to render (e.g., 'user_list.html').
    :param search_fields: A dictionary where keys are request GET parameters and values are model fields to filter by.
    :param sort_field: The default field for sorting (e.g., '-updated_at').
    :param extra_context: Any additional context data needed in the template.
    :param add: Whether to include Add action in the template.
    :param actions: Whether to include Edit/Delete actions in the template.
    :return: Rendered response with paginated and filtered object list.
    """
    objects = model.objects.all()

    # Apply search filters dynamically
    search_values = {}
    if search_fields:
        for param, field in search_fields.items():
            value = request.GET.get(param, '').strip()
            if value:
                objects = objects.filter(**{f"{field}__icontains": value})
            search_values[param] = value  # Preserve search values

    # To fix the warning: UnorderedObjectListWarning: Pagination may yield inconsistent results with an unordered object_list: <class 'django.contrib.auth.models.User'> QuerySet.
    # Check if the model has Meta ordering; if not, sort by id
    default_ordering = getattr(model._meta, "ordering", None) or ["id"]
    objects = objects.order_by(*default_ordering)

    # Handle sorting based on user selection
    sort_by = request.GET.get('sort_by', '')  # Default is empty
    if sort_fields and sort_by in sort_fields:  # Ensure sort_fields is not None
        objects = objects.order_by(sort_by)

    # Paginate results
    paginator = Paginator(objects, 10)  # nubmer of rows per page
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    context = {
        'title': extra_context.get('title', model._meta.verbose_name.capitalize()) if extra_context else model._meta.verbose_name.capitalize(),
        'page_obj': page_obj,
        'columns': columns,
        'search_queries': {param: request.GET.get(param, '') for param in search_fields} if search_fields else {},
        'sort_queries': sort_fields,
        'add': add,
        'actions': actions,  # Determines whether to show Edit/Delete buttons
    }

    # Merge extra context if provided
    if extra_context:
        context.update(extra_context)

    return render(request, 'list_page.html', context)
