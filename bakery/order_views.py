"""
Order detail view for displaying complete order information
"""
from django.shortcuts import render, get_object_or_404
from django.contrib.auth.decorators import login_required
from bakery.models import Order, Receipt
from decimal import Decimal


@login_required
def order_detail_view(request, order_reference):
    """Display complete order details including all items and summary"""
    # Get all orders with this reference number for the logged-in user
    order_items = Order.objects.filter(
        reference_number=order_reference,
        user=request.user
    ).order_by('ordered_at')
    
    # Ensure at least one order exists
    if not order_items.exists():
        return get_object_or_404(Order)  # This will raise 404
    
    # Get the first order for basic info (they all share session_id and dates)
    order = order_items.first()
    
    # Get receipt if it exists
    receipt = Receipt.objects.filter(
        session_id=order.session_id,
        user=request.user
    ).first()
    
    # Calculate totals
    item_details = []
    total_items = 0
    subtotal = Decimal('0.00')
    
    for item in order_items:
        line_total = item.item_price * item.quantity
        item_details.append({
            'name': item.item_name,
            'quantity': item.quantity,
            'unit_price': item.item_price,
            'line_total': line_total
        })
        total_items += item.quantity
        subtotal += line_total
    
    # Shipping and discount (from receipt if available)
    shipping_fee = Decimal('0.00')
    discount = Decimal('0.00')
    if receipt:
        # Could extend this to store shipping/discount in Receipt model if needed
        pass
    
    grand_total = subtotal + shipping_fee - discount
    
    # Payment information
    payment_status = 'paid' if receipt and receipt.amount_paid else 'pending'
    amount_paid = receipt.amount_paid if receipt else Decimal('0.00')
    remaining_balance = receipt.remaining_balance if receipt else grand_total
    
    return render(request, 'order_detail.html', {
        'order': order,
        'receipt': receipt,
        'item_details': item_details,
        'total_items': total_items,
        'subtotal': subtotal,
        'shipping_fee': shipping_fee,
        'discount': discount,
        'grand_total': grand_total,
        'payment_status': payment_status,
        'amount_paid': amount_paid,
        'remaining_balance': remaining_balance,
    })
