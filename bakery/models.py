import logging
from django.db import models
from django.contrib.auth.models import User
from django.utils import timezone
from datetime import timedelta

class UserProfile(models.Model):
    ROLE_CHOICES = [
        ('customer', 'Customer'),
        ('staff', 'Staff'),
        ('admin', 'Admin'),
    ]
    
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='profile')
    contactnumber = models.CharField(max_length=11)
    role = models.CharField(max_length=20, choices=ROLE_CHOICES, default='customer')
    is_active = models.BooleanField(default=True)
    mfa_sms_enabled = models.BooleanField(default=False)
    mfa_email_enabled = models.BooleanField(default=False)
    failed_login_attempts = models.IntegerField(default=0)
    lockout_until = models.DateTimeField(null=True, blank=True)

    def __str__(self):
        return f"Profile for {self.user.username} ({self.role})"

    def is_locked(self):
        """Check if account is currently locked"""
        if self.lockout_until and timezone.now() < self.lockout_until:
            return True
        return False

    def increment_failed_attempts(self):
        """Increment failed login attempts and lock if threshold reached"""
        self.failed_login_attempts += 1
        if self.failed_login_attempts >= 5:
            # Lock account for 30 minutes
            self.lockout_until = timezone.now() + timedelta(minutes=30)
        self.save()

    def reset_failed_attempts(self):
        """Reset failed login attempts on successful login"""
        self.failed_login_attempts = 0
        self.lockout_until = None
        self.save()

class MFACode(models.Model):
    """Stores temporary 2FA verification codes"""
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='mfa_code')
    code = models.CharField(max_length=6)
    method = models.CharField(max_length=10, choices=[('sms', 'SMS'), ('email', 'Email')])
    created_at = models.DateTimeField(auto_now_add=True)
    expires_at = models.DateTimeField()
    is_verified = models.BooleanField(default=False)
    
    def is_expired(self):
        return timezone.now() > self.expires_at
    
    def __str__(self):
        return f"MFA Code for {self.user.username} ({self.method})"

class Product(models.Model):
    name = models.CharField(max_length=255, unique=True)
    price = models.DecimalField(max_digits=10, decimal_places=2)
    image = models.ImageField(upload_to='products/', default='images/tab.png')
    description = models.TextField(blank=True, default='')
    stock = models.PositiveIntegerField(default=0)
    is_available = models.BooleanField(default=True)

    def __str__(self):
        return self.name

class CartItem(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='cart_items')
    product = models.ForeignKey(Product, on_delete=models.CASCADE)
    quantity = models.PositiveIntegerField(default=1)

    def __str__(self):
        return f"{self.user.username} - {self.product.name} ({self.quantity})"

class Order(models.Model):
    STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('confirmed', 'Confirmed'),
        ('preparing', 'Preparing'),
        ('ready', 'Ready for Pickup'),
        ('completed', 'Completed'),
        ('cancelled', 'Cancelled'),
    ]
    
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='orders')
    session_id = models.CharField(max_length=64)
    item_name = models.CharField(max_length=255)
    item_price = models.DecimalField(max_digits=10, decimal_places=2)
    ordered_at = models.DateTimeField(auto_now_add=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')

    def __str__(self):
        return f"Order {self.id} for {self.user.username} ({self.status})"

class Receipt(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='receipts')
    session_id = models.CharField(max_length=64)
    order_date = models.DateTimeField(auto_now_add=True)
    total_price = models.DecimalField(max_digits=10, decimal_places=2)
    housenumber = models.CharField(max_length=55)
    streetname = models.CharField(max_length=55)
    barangay = models.CharField(max_length=55)
    postalcode = models.CharField(max_length=55)
    city = models.CharField(max_length=55)

    def __str__(self):
        return f"Receipt {self.id} for {self.user.username}"

class UserActivity(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='activities')
    activity_type = models.CharField(max_length=20, choices=[('login', 'Login'), ('logout', 'Logout')])
    timestamp = models.DateTimeField(auto_now_add=True)
    ip_address = models.GenericIPAddressField(null=True, blank=True)

    class Meta:
        ordering = ['-timestamp']

    def __str__(self):
        return f"{self.user.username} - {self.activity_type} at {self.timestamp}"

class AuditLog(models.Model):
    ACTION_CHOICES = [
        ('product_create', 'Product Created'),
        ('product_edit', 'Product Edited'),
        ('product_delete', 'Product Deleted'),
        ('order_status_update', 'Order Status Updated'),
        ('staff_create', 'Staff Account Created'),
        ('staff_edit', 'Staff Account Edited'),
        ('staff_deactivate', 'Staff Account Deactivated'),
        ('staff_activate', 'Staff Account Activated'),
    ]
    
    user = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, related_name='audit_logs')
    action = models.CharField(max_length=30, choices=ACTION_CHOICES)
    description = models.TextField()
    timestamp = models.DateTimeField(auto_now_add=True)
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    
    # Related objects (optional)
    product_id = models.IntegerField(null=True, blank=True)
    order_id = models.IntegerField(null=True, blank=True)
    target_user_id = models.IntegerField(null=True, blank=True)

    class Meta:
        ordering = ['-timestamp']

    def __str__(self):
        return f"{self.user.username if self.user else 'System'} - {self.action} at {self.timestamp}"

    def save(self, *args, **kwargs):
        super().save(*args, **kwargs)
        try:
            logger = logging.getLogger('security')
            user_str = self.user.username if self.user else 'System'
            logger.info(
                f"AUDIT_LOG | Action: {self.action} | User: {user_str} | IP: {self.ip_address or 'N/A'} | Description: {self.description}"
            )
        except Exception:
            pass
