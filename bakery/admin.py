from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from django.contrib.auth.models import User
from django.contrib.auth.forms import UserCreationForm
from django import forms
from django.shortcuts import redirect, render
from django.contrib.auth import authenticate, login as auth_login
from django.urls import path
from .models import UserActivity, UserProfile, Product, CartItem, Order, Receipt, AuditLog, TOTPSecret


# ── Custom Admin Site with TOTP ──────────────────────────────────────────────

class TOTPAdminSite(admin.AdminSite):
    """Custom admin site that requires TOTP verification for superusers/staff"""

    def login(self, request, extra_context=None):
        """Override login to handle TOTP requirement"""
        if request.method == 'POST':
            username = request.POST.get('username')
            password = request.POST.get('password')

            user = authenticate(request, username=username, password=password)

            if user is not None:
                # User authenticated successfully
                # Check if user is superuser or admin/staff
                is_admin_user = user.is_superuser or (
                    hasattr(user, 'profile') and user.profile.role in ['admin', 'staff']
                )

                if is_admin_user:
                    # Check if user has TOTP enabled
                    try:
                        totp_secret = user.totp_secret
                        if totp_secret.is_verified:
                            # TOTP enabled - store user ID in session for verification
                            request.session['totp_user_id'] = user.id
                            request.session['totp_pending_username'] = username
                            return redirect('admin:verify_admin_totp')
                    except TOTPSecret.DoesNotExist:
                        # User is admin but hasn't set up TOTP yet
                        # Store for potential future enforcement
                        pass

                    # If no TOTP or user is admin/staff without TOTP, allow login for now
                    # (TOTP setup can be optional or enforced later)
                    auth_login(request, user)
                    return redirect(self.index_url)
                else:
                    # Regular user - not allowed in admin
                    # Fall back to parent login which will show error
                    return super().login(request, extra_context=extra_context)
            else:
                # Authentication failed - fall back to parent
                return super().login(request, extra_context=extra_context)

        return super().login(request, extra_context=extra_context)

    def get_urls(self):
        """Add TOTP URLs to admin site"""
        from bakery import views
        urls = super().get_urls()
        custom_urls = [
            path('totp/setup/', self.admin_view(views.admin_totp_setup), name='admin_totp_setup'),
            path('totp/disable/', self.admin_view(views.admin_totp_disable), name='admin_totp_disable'),
            path('totp/verify/', views.verify_admin_totp, name='verify_admin_totp'),
        ]
        return custom_urls + urls

class StaffUserCreationForm(UserCreationForm):
    email = forms.EmailField(required=True, label="Email")

    class Meta:
        model = User
        fields = ("email", "password1", "password2")

    def save(self, commit=True):
        user = super().save(commit=False)
        # Use email as username (must be unique)
        user.username = self.cleaned_data["email"]
        user.email = self.cleaned_data["email"]
        user.is_staff = True          # mark as staff
        user.is_superuser = False     # never superuser
        if commit:
            user.save()
            # Create or update UserProfile safely
            UserProfile.objects.update_or_create(
                user=user,
                defaults={"role": "staff", "is_active": True}
            )
        return user


# ── Inline for existing users ────────────────────────────────────────────────

class UserProfileInline(admin.StackedInline):
    model = UserProfile
    can_delete = False
    verbose_name_plural = "Profile"
    # Make contactnumber optional in admin so it doesn't block saving
    extra = 0

    def get_fields(self, request, obj=None):
        return ("contactnumber", "role", "is_active", "mfa_sms_enabled", "mfa_email_enabled")


# ── Custom UserAdmin ─────────────────────────────────────────────────────────

class StaffUserAdmin(BaseUserAdmin):
    add_form = StaffUserCreationForm
    inlines = (UserProfileInline,)

    list_display = ("username", "email", "is_staff", "is_superuser", "is_active")
    list_filter = ("is_staff", "is_superuser", "is_active")

    # Fields shown when EDITING an existing user
    fieldsets = (
        (None, {"fields": ("username", "email", "password")}),
        ("Permissions", {"fields": ("is_active", "is_staff", "is_superuser")}),
    )

    # Fields shown when ADDING a new user — only email + password
    add_fieldsets = (
        (None, {
            "classes": ("wide",),
            "fields": ("email", "password1", "password2"),
        }),
    )

    def save_model(self, request, obj, form, change):
        super().save_model(request, obj, form, change)
        # For existing users edited via admin, ensure UserProfile exists
        if change:
            UserProfile.objects.get_or_create(user=obj)

    def get_inline_instances(self, request, obj=None):
        # Only show the inline when editing, NOT when adding
        # (the add form handles profile creation itself)
        if obj is None:
            return []
        return super().get_inline_instances(request, obj)


# ── Register all models ──────────────────────────────────────────────────────

# Unregister default admin site and register custom TOTP admin site
admin.site.__class__ = TOTPAdminSite

admin.site.unregister(User)
admin.site.register(User, StaffUserAdmin)


@admin.register(UserProfile)
class UserProfileAdmin(admin.ModelAdmin):
    list_display = ("user", "contactnumber", "role", "is_active")


@admin.register(Product)
class ProductAdmin(admin.ModelAdmin):
    list_display = ("name", "price", "stock", "is_available")


@admin.register(Order)
class OrderAdmin(admin.ModelAdmin):
    list_display = ("id", "user", "item_name", "item_price", "status", "ordered_at")


@admin.register(CartItem)
class CartItemAdmin(admin.ModelAdmin):
    list_display = ("user", "product", "quantity")


@admin.register(Receipt)
class ReceiptAdmin(admin.ModelAdmin):
    list_display = ("user", "order_date", "total_price")


@admin.register(UserActivity)
class UserActivityAdmin(admin.ModelAdmin):
    list_display = ("user", "activity_type", "timestamp", "ip_address")
    readonly_fields = ("timestamp",)


@admin.register(AuditLog)
class AuditLogAdmin(admin.ModelAdmin):
    list_display = ("id", "user", "action", "timestamp")
    readonly_fields = ("timestamp",)

@admin.register(TOTPSecret)
class TOTPSecretAdmin(admin.ModelAdmin):
    list_display = ("user", "is_verified", "created_at")
    readonly_fields = ("secret", "created_at")
    search_fields = ("user__email",)