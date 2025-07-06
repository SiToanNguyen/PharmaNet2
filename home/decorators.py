# home/decorators.py
from functools import wraps
from django.contrib.auth.decorators import user_passes_test
from django.contrib import messages
from django.shortcuts import redirect

def superuser_required(view_func):
    '''
    Decorator to check if the user is a superuser.
    If the user is not a superuser, they will be redirected to the admin login page.
    '''
    decorated_view_func = user_passes_test(
        lambda u: u.is_active and u.is_superuser,
        login_url='admin:login',
        redirect_field_name=None
    )(view_func)
    return decorated_view_func

def superuser_required_403(view_func):
    '''
    Decorator to check if the user is a superuser.
    If the user is not logged in, they will be redirected to the login page.
    If the user is not a superuser, they will be redirected to the previous page with an error message.
    '''
    @wraps(view_func)
    def _wrapped_view(request, *args, **kwargs):
        if not request.user.is_authenticated:
            messages.error(request, "You must be logged in to access this page.")
            return redirect('login')
        if not request.user.is_superuser:
            messages.error(request, "You do not have permission to perform this action.")
            return redirect(request.META.get('HTTP_REFERER', 'homepage'))  # fallback to homepage
        return view_func(request, *args, **kwargs)
    return _wrapped_view