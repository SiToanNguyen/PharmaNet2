from django.shortcuts import redirect
from django.urls import reverse
from django.conf import settings
from django.contrib.auth import logout

class LoginRequiredMiddleware:
    """
    Middleware to ensure the user is logged in for all requests except login, static files, and APIs.
    """
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        excluded_paths = [
            reverse('login'),  # Adjust if your login URL name is different
            '/static/',        # Static files
            '/api/'            # Optional: API endpoints
        ]

        # Check if the user is authenticated
        if not request.user.is_authenticated:
            # Bypass login check for excluded paths
            if not any(request.path.startswith(path) for path in excluded_paths):
                return redirect('login')  # Redirect to the login page
        
        response = self.get_response(request)
        return response
