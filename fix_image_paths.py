import os
import django
from pathlib import Path

# Set up Django environment
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'dough_re_mi.settings')
django.setup()

from bakery.models import Product

# Mapping of database filenames to actual filenames in images folder
filename_mapping = {
    'products/ouioui.png': 'images/baguette.png',
    'products/plaincroissant.png': 'images/croissant.png',
    'products/eclair_lQe9F8Y.png': 'images/Eclair.png',
    'products/flavoured_croissant.jpg': 'images/CA.jpg',
}

# Fix image paths using the mapping
products = Product.objects.all()
for product in products:
    if product.image:
        old_image = str(product.image)
        
        # Check if this filename is in our mapping
        if old_image in filename_mapping:
            new_image = filename_mapping[old_image]
            product.image = new_image
            product.save()
            print(f"Updated {product.name}: {old_image} -> {new_image}")

print("Image paths fixed successfully!")
