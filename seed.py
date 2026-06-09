import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'dough_re_mi.settings')
django.setup()

from bakery.models import Product

products = [
    {"name": "Classic Croissant", "price": 40.00, "image": "images/croissant.png"},
    {"name": "Medium Baguette", "price": 89.00, "image": "images/baguette.png"},
    {"name": "Strawberry Macaroons", "price": 30.00, "image": "images/Strawberry Macaroons.png"},
    {"name": "Eclair", "price": 25.00, "image": "images/Eclair.png"},
    {"name": "Pan au Chocolat", "price": 45.00, "image": "images/Pan au Chocolat.png"},
    {"name": "Paris-Brest", "price": 129.00, "image": "images/Paris-Brest.png"},
]

for p in products:
    Product.objects.get_or_create(name=p['name'], defaults={'price': p['price'], 'image': p['image']})

print("Products seeded successfully.")
