# home/decorators.py
from django.contrib.auth.decorators import user_passes_test
from django.core.exceptions import PermissionDenied

def superuser_required(view_func):
    decorated_view_func = user_passes_test(
        lambda u: u.is_active and u.is_superuser,
        login_url='admin:login',  # or your custom login URL
        redirect_field_name=None
    )(view_func)
    return decorated_view_func
