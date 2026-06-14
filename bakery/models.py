from django.db import models
from django.contrib.auth.models import User
from django.utils import timezone

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

    def __str__(self):
        return f"Profile for {self.user.username} ({self.role})"

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
    
    PAYMENT_OPTION_CHOICES = [
        ('full', 'Full Payment'),
        ('partial', 'Partial Payment'),
    ]
    
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='orders')
    session_id = models.CharField(max_length=64)
    item_name = models.CharField(max_length=255)
    item_price = models.DecimalField(max_digits=10, decimal_places=2)
    ordered_at = models.DateTimeField(auto_now_add=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    reference_number = models.CharField(max_length=20, unique=True, null=True, blank=True)
    payment_option = models.CharField(max_length=20, choices=PAYMENT_OPTION_CHOICES, null=True, blank=True)
    total_amount = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    amount_paid = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    remaining_balance = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    pickup_availability_date = models.DateField(null=True, blank=True)

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

def generate_order_reference_number():
    """Generate a unique order reference number in format DRMP-YYYY-XXXXXX"""
    year = timezone.now().year
    # Get the last reference number for this year
    last_receipt = Receipt.objects.filter(
        reference_number__startswith=f'DRMP-{year}-'
    ).order_by('-id').first()
    
    if last_receipt:
        # Extract the numeric part and increment
        last_num = int(last_receipt.reference_number.split('-')[-1])
        new_num = last_num + 1
    else:
        new_num = 1
    
    # Format as DRMP-YYYY-XXXXXX (6 digits with leading zeros)
    return f'DRMP-{year}-{new_num:06d}'

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
