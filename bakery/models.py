import logging
from django.db import models
from django.contrib.auth.models import User
from django.utils import timezone
from datetime import timedelta
from decimal import Decimal

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
    has_set_password = models.BooleanField(default=False, help_text="Whether user has set their own password (for staff accounts)")

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
    attempts = models.IntegerField(default=0)
    verified_at = models.DateTimeField(null=True, blank=True)

    def is_expired(self):
        return timezone.now() > self.expires_at

    def __str__(self):
        return f"MFA Code for {self.user.username} ({self.method})"

class TOTPSecret(models.Model):
    """Stores TOTP secrets for admin users"""
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='totp_secret')
    secret = models.CharField(max_length=32, unique=True)
    is_verified = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    backup_codes = models.JSONField(default=list, blank=True)

    def __str__(self):
        return f"TOTP for {self.user.username}"

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
        ('processing', 'Processing'),
        ('claimed', 'Claimed'),
        ('confirmed', 'Confirmed'),
        ('preparing', 'Preparing'),
        ('ready', 'Ready for Pickup'),
        ('completed', 'Completed'),
        ('cancelled', 'Cancelled'),
    ]
    
    PAYMENT_OPTION_CHOICES = [
        ('full', 'Full Payment'),
        ('partial', 'Partial Payment'),
    ]
    
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='orders')
    session_id = models.CharField(max_length=64)
    item_name = models.CharField(max_length=255)
    item_price = models.DecimalField(max_digits=10, decimal_places=2)
    quantity = models.PositiveIntegerField(default=1, help_text="Quantity of this item in the order")
    ordered_at = models.DateTimeField(auto_now_add=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    reference_number = models.CharField(max_length=20, null=True, blank=True)
    payment_option = models.CharField(max_length=20, choices=PAYMENT_OPTION_CHOICES, null=True, blank=True)
    total_amount = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    amount_paid = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    remaining_balance = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    pickup_availability_date = models.DateField(null=True, blank=True)
    contact_number = models.CharField(max_length=11, null=True, blank=True, help_text="Customer contact number")
    processed_at = models.DateTimeField(null=True, blank=True, help_text="Date and time when order was moved to Processing")
    claimed_at = models.DateTimeField(null=True, blank=True, help_text="Date and time when order was claimed")
    updated_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='updated_orders', help_text="Staff member who last updated the order status")

    def get_order_total(self):
        """Calculate total for all items in this order (by session_id)"""
        all_items = Order.objects.filter(session_id=self.session_id)
        total = Decimal('0.00')
        for item in all_items:
            total += item.item_price * item.quantity
        return total
    
    def get_order_items(self):
        """Get all items in this order (by session_id)"""
        return Order.objects.filter(session_id=self.session_id).select_related('user')
    
    def __str__(self):
        return f"Order {self.id} for {self.user.username} ({self.status})"

class Receipt(models.Model):
    PAYMENT_OPTION_CHOICES = [
        ('full', 'Full Payment'),
        ('partial', 'Partial Payment'),
    ]
    
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='receipts')
    session_id = models.CharField(max_length=64)
    order_date = models.DateTimeField(auto_now_add=True)
    total_price = models.DecimalField(max_digits=10, decimal_places=2)
    full_name = models.CharField(max_length=255, null=True, blank=True)
    contact_number = models.CharField(max_length=11, null=True, blank=True)
    reference_number = models.CharField(max_length=20, unique=True, null=True, blank=True)
    payment_option = models.CharField(max_length=20, choices=PAYMENT_OPTION_CHOICES, null=True, blank=True)
    total_amount = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    amount_paid = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    remaining_balance = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    pickup_availability_date = models.DateField(null=True, blank=True)

    def __str__(self):
        return f"Receipt {self.id} for {self.user.username}"

class Payment(models.Model):
    STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('paid', 'Paid'),
        ('failed', 'Failed'),
        ('refunded', 'Refunded'),
    ]
    
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='payments')
    receipt = models.ForeignKey(Receipt, on_delete=models.CASCADE, related_name='payments', null=True, blank=True)
    paymongo_payment_id = models.CharField(max_length=100, unique=True, null=True, blank=True)
    paymongo_checkout_id = models.CharField(max_length=100, unique=True, null=True, blank=True)
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    payment_date = models.DateTimeField(auto_now_add=True)
    payment_method = models.CharField(max_length=50, null=True, blank=True)
    raw_response = models.JSONField(null=True, blank=True)

    def __str__(self):
        return f"Payment {self.id} for {self.user.username} ({self.status})"

def generate_order_reference_number(order_date=None):
    """Generate a unique order reference number in format DRMP-YYYY-MM-DD-XXXX
    
    Args:
        order_date: The date to use for the reference. Defaults to today.
    """
    if order_date is None:
        order_date = timezone.now().date()
    
    # Handle datetime objects
    if hasattr(order_date, 'date'):
        order_date = order_date.date()
    
    prefix = f'DRMP-{order_date:%Y-%m-%d}-'

    # Get all references for this date
    references = list(Receipt.objects.filter(
        reference_number__startswith=prefix
    ).values_list('reference_number', flat=True))
    references += list(Order.objects.filter(
        reference_number__startswith=prefix
    ).values_list('reference_number', flat=True))

    # Remove duplicates and find max number
    references = set(ref for ref in references if ref)
    max_num = 0
    for ref in references:
        try:
            candidate = int(ref.split('-')[-1])
            if candidate > max_num:
                max_num = candidate
        except (ValueError, IndexError):
            continue

    new_num = max_num + 1
    return f'{prefix}{new_num:04d}'

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
        ('stock_validation_failed', 'Stock Validation Failed'),
        ('per_product_limit_failed', 'Per-Product Limit Failed'),
        ('cart_capacity_failed', 'Cart Capacity Failed'),
        ('order_cooldown_failed', 'Order Cooldown Failed'),
        ('daily_order_limit_failed', 'Daily Order Limit Failed'),
        ('cart_add_error', 'Cart Add Error'),
        ('order_created', 'Order Created'),
        ('payment_success', 'Payment Success'),
        ('payment_failed', 'Payment Failed'),
        ('payment_verification_failed', 'Payment Verification Failed'),
        ('pickup_completed', 'Pickup Completed'),
        ('stock_deducted', 'Stock Deducted'),
        ('stock_insufficient', 'Stock Insufficient'),
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

class InventoryLog(models.Model):
    """Track inventory changes for audit purposes"""
    CHANGE_TYPE_CHOICES = [
        ('deduction', 'Stock Deduction'),
        ('restock', 'Stock Restock'),
        ('adjustment', 'Stock Adjustment'),
        ('initial', 'Initial Stock'),
    ]
    
    product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name='inventory_logs')
    change_type = models.CharField(max_length=20, choices=CHANGE_TYPE_CHOICES)
    quantity_change = models.IntegerField()  # Positive for addition, negative for deduction
    previous_stock = models.IntegerField()
    new_stock = models.IntegerField()
    order_id = models.IntegerField(null=True, blank=True)
    payment_id = models.IntegerField(null=True, blank=True)
    user = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, related_name='inventory_changes')
    timestamp = models.DateTimeField(auto_now_add=True)
    notes = models.TextField(blank=True)

    class Meta:
        ordering = ['-timestamp']

    def __str__(self):
        return f"{self.product.name}: {self.change_type} ({self.quantity_change}) at {self.timestamp}"
