"""
Management command to fix existing orders with bad reference numbers.
Usage: python manage.py fix_order_references
"""
from django.core.management.base import BaseCommand
from bakery.models import Order, Receipt, generate_order_reference_number
from django.db.models import Q


class Command(BaseCommand):
    help = 'Fix existing orders with random/bad reference numbers'

    def handle(self, *args, **options):
        # Get all orders, ordered by date
        all_orders = Order.objects.all().order_by('ordered_at')
        
        self.stdout.write(self.style.SUCCESS(f'Found {all_orders.count()} orders'))
        
        reference_map = {}  # Map session_id to new reference
        updated_count = 0
        
        for order in all_orders:
            session_id = order.session_id
            
            # Skip if already has a good reference
            if order.reference_number and order.reference_number.startswith('DRMP-'):
                reference_map[session_id] = order.reference_number
                continue
            
            # Generate reference if this session doesn't have one yet
            if session_id not in reference_map:
                reference_number = generate_order_reference_number(order.ordered_at)
                reference_map[session_id] = reference_number
            else:
                reference_number = reference_map[session_id]
            
            # Update this order
            if order.reference_number != reference_number:
                old_ref = order.reference_number
                order.reference_number = reference_number
                order.save()
                updated_count += 1
                self.stdout.write(
                    f'Updated order {order.id}: {old_ref} -> {reference_number}'
                )
        
        # Also update receipts
        receipt_updates = 0
        for receipt in Receipt.objects.all():
            if not receipt.reference_number or not receipt.reference_number.startswith('DRMP-'):
                # Try to find the reference from associated orders
                order = Order.objects.filter(session_id=receipt.session_id).first()
                if order and order.reference_number:
                    old_ref = receipt.reference_number
                    receipt.reference_number = order.reference_number
                    receipt.save()
                    receipt_updates += 1
                    self.stdout.write(
                        f'Updated receipt {receipt.id}: {old_ref} -> {order.reference_number}'
                    )
        
        self.stdout.write(
            self.style.SUCCESS(
                f'Successfully updated {updated_count} orders and {receipt_updates} receipts'
            )
        )
