from django.shortcuts import redirect
from django.conf import settings

class RequirePasswordMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        if request.user.is_authenticated and not request.user.has_usable_password():
            # Allow access to set password page, logout, static/admin, and cart API endpoints
            allowed_paths = ['/set-password', '/logout', '/admin/', '/static/', '/media/', '/add-to-cart.php', '/remove-from-cart.php', '/update-cart-quantity.php', '/get-cart.php', '/checkout.php']
            if not any(request.path.startswith(path) for path in allowed_paths):
                return redirect('set_password')
        
        response = self.get_response(request)
        return response

class RoleBasedRedirectMiddleware:
    """
    Middleware to redirect users based on their role after login.
    Only applies to GET requests to avoid interfering with AJAX calls.
    """
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        # Only apply to GET requests to login page to avoid interfering with AJAX calls
        # Also check if there's a 'next' parameter to preserve intended destination
        if request.method == 'GET' and request.path in ['/login', '/login.php'] and request.user.is_authenticated:
            # If there's a next parameter, don't redirect - let the user continue to their intended destination
            if 'next' in request.GET:
                response = self.get_response(request)
                return response
            
            if request.user.is_superuser:
                return redirect('/admin/')
            elif hasattr(request.user, 'profile'):
                if request.user.profile.role == 'staff':
                    return redirect('staff_dashboard')
                elif request.user.profile.role == 'customer':
                    return redirect('index')
        
        response = self.get_response(request)
        return response
