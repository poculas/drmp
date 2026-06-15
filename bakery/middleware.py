from django.shortcuts import redirect
from django.conf import settings

class RequirePasswordMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        if request.user.is_authenticated and not request.user.has_usable_password():
            # Allow access to set password page, logout, and static/admin
            allowed_paths = ['/set-password', '/logout', '/admin/', '/static/', '/media/']
            if not any(request.path.startswith(path) for path in allowed_paths):
                return redirect('set_password')
        
        response = self.get_response(request)
        return response

class RoleBasedRedirectMiddleware:
    """
    Middleware to redirect users based on their role after login.
    """
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        # Only apply to login redirect (both /login and /login.php)
        if request.path in ['/login', '/login.php'] and request.user.is_authenticated:
            if request.user.is_superuser:
                return redirect('/admin/')
            elif hasattr(request.user, 'profile'):
                if request.user.profile.role == 'staff':
                    return redirect('staff_dashboard')
                elif request.user.profile.role == 'customer':
                    return redirect('index')
        
        response = self.get_response(request)
        return response
