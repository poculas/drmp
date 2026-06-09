from django.db import models
from django.contrib.auth.models import User

class UserProfile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='profile')
    contactnumber = models.CharField(max_length=11)

    def __str__(self):
        return f"Profile for {self.user.username}"

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
