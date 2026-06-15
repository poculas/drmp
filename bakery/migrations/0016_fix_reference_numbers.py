# Generated migration to fix existing order references

from django.db import migrations
from django.utils import timezone
from decimal import Decimal


def fix_order_references(apps, schema_editor):
    """Fix existing orders with random/bad reference numbers"""
    Order = apps.get_model('bakery', 'Order')
    Receipt = apps.get_model('bakery', 'Receipt')
    
    # Get all orders with bad references (random letters/short strings)
    all_orders = Order.objects.all().order_by('ordered_at')
    
    reference_map = {}  # Map old session_id to new reference
    
    for order in all_orders:
        session_id = order.session_id
        
        # Generate reference if this session doesn't have one yet
        if session_id not in reference_map:
            # Generate using the order's purchase date
            order_date = order.ordered_at.date()
            prefix = f'DRMP-{order_date:%Y-%m-%d}-'
            
            # Find the next number for this date
            existing_refs = set()
            for o in Order.objects.filter(reference_number__startswith=prefix).values_list('reference_number', flat=True):
                if o:
                    existing_refs.add(o)
            for r in Receipt.objects.filter(reference_number__startswith=prefix).values_list('reference_number', flat=True):
                if r:
                    existing_refs.add(r)
            
            # Extract numbers and find max
            max_num = 0
            for ref in existing_refs:
                try:
                    num = int(ref.split('-')[-1])
                    if num > max_num:
                        max_num = num
                except (ValueError, IndexError):
                    pass
            
            new_num = max_num + 1
            reference_map[session_id] = f'{prefix}{new_num:04d}'
        
        # Update this order with the reference
        if not order.reference_number or not order.reference_number.startswith('DRMP-'):
            order.reference_number = reference_map[session_id]
            order.save()
    
    # Also update receipts
    for receipt in Receipt.objects.all():
        if not receipt.reference_number or not receipt.reference_number.startswith('DRMP-'):
            # Try to find the reference from associated orders
            order = Order.objects.filter(session_id=receipt.session_id).first()
            if order and order.reference_number:
                receipt.reference_number = order.reference_number
                receipt.save()


class Migration(migrations.Migration):

    dependencies = [
        ('bakery', '0015_alter_order_reference_number'),
    ]

    operations = [
        migrations.RunPython(fix_order_references),
    ]
