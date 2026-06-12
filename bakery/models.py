from django.db import models
from django.contrib.auth.models import User
from django.utils import timezone
from datetime import timedelta

class UserProfile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='profile')
    contactnumber = models.CharField(max_length=11)
    mfa_sms_enabled = models.BooleanField(default=False)
    mfa_email_enabled = models.BooleanField(default=False)
    failed_login_attempts = models.IntegerField(default=0)
    lockout_until = models.DateTimeField(null=True, blank=True)

    def __str__(self):
        return f"Profile for {self.user.username}"

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
    image = models.CharField(max_length=255, default='images/tab.png')
    description = models.TextField(blank=True, default='')

    def __str__(self):
        return self.name

class CartItem(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='cart_items')
    product = models.ForeignKey(Product, on_delete=models.CASCADE)
    quantity = models.PositiveIntegerField(default=1)

    def __str__(self):
        return f"{self.user.username} - {self.product.name} ({self.quantity})"

class Order(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='orders')
    session_id = models.CharField(max_length=64)
    item_name = models.CharField(max_length=255)
    item_price = models.DecimalField(max_digits=10, decimal_places=2)
    ordered_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Order {self.id} for {self.user.username}"

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
