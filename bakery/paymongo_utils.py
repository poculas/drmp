import requests
import json
import base64
from django.conf import settings
from django.utils import timezone
from django.db import transaction
from bakery.models import Payment, Receipt, Order, AuditLog, InventoryLog, Product


@transaction.atomic
def deduct_stock_for_orders(session_id, payment_id, user):
    """
    Atomically deduct stock for all orders in a session after successful payment.
    
    Args:
        session_id (str): The session ID for the orders
        payment_id (int): The payment ID for audit logging
        user: The user who made the payment
        
    Returns:
        dict: Result with success status and details
    """
    try:
        # Get all orders for this session
        orders = Order.objects.filter(session_id=session_id).select_for_update()
        
        if not orders:
            return {'success': True, 'message': 'No orders found for stock deduction'}
        
        stock_deduction_results = []
        insufficient_stock_items = []
        
        for order in orders:
            # Find the product by name
            try:
                product = Product.objects.filter(name=order.item_name).select_for_update().first()
                if not product:
                    stock_deduction_results.append({
                        'product': order.item_name,
                        'status': 'product_not_found',
                        'quantity': order.quantity
                    })
                    continue
                
                # Check if sufficient stock is available
                if product.stock < order.quantity:
                    insufficient_stock_items.append({
                        'product': product.name,
                        'requested': order.quantity,
                        'available': product.stock
                    })
                    
                    # Log insufficient stock
                    AuditLog.objects.create(
                        user=user,
                        action='stock_insufficient',
                        description=f"Insufficient stock for {product.name}: requested {order.quantity}, available {product.stock}",
                        product_id=product.id,
                        order_id=order.id
                    )
                    continue
                
                # Deduct stock
                previous_stock = product.stock
                new_stock = product.stock - order.quantity
                product.stock = new_stock
                product.save()
                
                # Log inventory change
                InventoryLog.objects.create(
                    product=product,
                    change_type='deduction',
                    quantity_change=-order.quantity,
                    previous_stock=previous_stock,
                    new_stock=new_stock,
                    order_id=order.id,
                    payment_id=payment_id,
                    user=user,
                    notes=f"Stock deducted for order {order.id} after successful payment"
                )
                
                stock_deduction_results.append({
                    'product': product.name,
                    'status': 'success',
                    'quantity_deducted': order.quantity,
                    'previous_stock': previous_stock,
                    'new_stock': new_stock
                })
                
                # Log successful stock deduction
                AuditLog.objects.create(
                    user=user,
                    action='stock_deducted',
                    description=f"Stock deducted for {product.name}: {order.quantity} units (from {previous_stock} to {new_stock})",
                    product_id=product.id,
                    order_id=order.id
                )
                
            except Product.DoesNotExist:
                stock_deduction_results.append({
                    'product': order.item_name,
                    'status': 'product_not_found',
                    'quantity': order.quantity
                })
        
        if insufficient_stock_items:
            return {
                'success': False,
                'error': 'Insufficient stock for some items',
                'insufficient_items': insufficient_stock_items,
                'deduction_results': stock_deduction_results
            }
        
        return {
            'success': True,
            'message': f'Stock deducted for {len(stock_deduction_results)} items',
            'deduction_results': stock_deduction_results
        }
        
    except Exception as e:
        # Log error
        AuditLog.objects.create(
            user=user,
            action='stock_validation_failed',
            description=f"Stock deduction failed: {str(e)}",
            ip_address=None
        )
        return {
            'success': False,
            'error': f"Stock deduction failed: {str(e)}"
        }


def create_paymongo_checkout(amount, description, user):
    """
    Create a PayMongo checkout session for payment.
    
    Args:
        amount (float): The amount to charge in PHP
        description (str): Description of the payment
        user: The user making the payment
        
    Returns:
        dict: Response from PayMongo API with checkout URL
    """
    try:
        # Debug: Check if credentials are loaded
        if not settings.PAYMONGO_SECRET_KEY:
            return {
                'success': False,
                'error': 'PayMongo secret key not configured. Please add PAYMONGO_SECRET_KEY to .env file'
            }
        
        # PayMongo API endpoint for creating checkout sessions
        url = f"{settings.PAYMONGO_API_URL}/checkout_sessions"
        
        # Build redirect URLs
        base_url = getattr(settings, 'BASE_URL', 'http://127.0.0.1:8000')
        success_url = f"{base_url}/payment-success.php"
        failed_url = f"{base_url}/menu.php?payment=failed"
        
        # Get user profile information for pre-filling
        user_email = user.email
        user_name = f"{user.first_name} {user.userprofile.contactnumber if hasattr(user, 'userprofile') else ''}".strip()
        
        # PayMongo uses Basic Auth with secret key as username and empty password
        auth_string = f"{settings.PAYMONGO_SECRET_KEY}:"
        auth_bytes = auth_string.encode('utf-8')
        auth_base64 = base64.b64encode(auth_bytes).decode('utf-8')
        
        headers = {
            'Content-Type': 'application/json',
            'Authorization': f'Basic {auth_base64}',
            'accept': 'application/json'
        }
        
        data = {
            'data': {
                'attributes': {
                    'amount': int(amount * 100),  # PayMongo expects amount in cents
                    'description': description,
                    'currency': 'PHP',
                    'line_items': [
                        {
                            'name': description,
                            'amount': int(amount * 100),
                            'quantity': 1,
                            'currency': 'PHP'
                        }
                    ],
                    'payment_method_types': ['gcash', 'paymaya', 'card', 'grab_pay'],
                    'send_payment_receipt': True,
                    'success_url': success_url,
                    'cancel_url': failed_url,
                    'customer': {
                        'email': user_email,
                        'name': user_name
                    }
                }
            }
        }
        
        response = requests.post(url, headers=headers, json=data, timeout=30)
        response_data = response.json()
        
        if response.status_code == 200 or response.status_code == 201:
            checkout_id = response_data['data']['id']
            checkout_url = response_data['data']['attributes']['checkout_url']
            
            # Create payment record
            payment = Payment.objects.create(
                user=user,
                amount=amount,
                status='pending',
                paymongo_checkout_id=checkout_id,
                raw_response=response_data
            )
            
            return {
                'success': True,
                'checkout_url': checkout_url,
                'checkout_id': checkout_id,
                'payment_id': payment.id
            }
        else:
            # Log payment failure
            AuditLog.objects.create(
                user=user,
                action='payment_failed',
                description=f"PayMongo checkout creation failed: {response_data.get('errors', 'Unknown error')}",
                ip_address=None
            )
            
            return {
                'success': False,
                'error': response_data.get('errors', 'Failed to create checkout session')
            }
            
    except requests.exceptions.RequestException as e:
        AuditLog.objects.create(
            user=user,
            action='payment_failed',
            description=f"PayMongo API request failed: {str(e)}",
            ip_address=None
        )
        
        return {
            'success': False,
            'error': f"Payment service unavailable: {str(e)}"
        }


def verify_paymongo_payment(checkout_id):
    """
    Verify the status of a PayMongo payment using the checkout ID.
    
    Args:
        checkout_id (str): The PayMongo checkout session ID
        
    Returns:
        dict: Payment verification result with status and details
    """
    try:
        # PayMongo API endpoint for retrieving checkout session
        url = f"{settings.PAYMONGO_API_URL}/checkout_sessions/{checkout_id}"
        
        # PayMongo uses Basic Auth with secret key as username and empty password
        auth_string = f"{settings.PAYMONGO_SECRET_KEY}:"
        auth_bytes = auth_string.encode('utf-8')
        auth_base64 = base64.b64encode(auth_bytes).decode('utf-8')
        
        headers = {
            'Content-Type': 'application/json',
            'Authorization': f'Basic {auth_base64}',
            'accept': 'application/json'
        }
        
        response = requests.get(url, headers=headers, timeout=30)
        response_data = response.json()
        
        if response.status_code == 200:
            payment_status = response_data['data']['attributes']['status']
            payment_intent_id = response_data['data']['attributes']['payment_intent_id']
            
            # Get payment details if payment is successful
            if payment_status == 'paid':
                # Retrieve payment intent details
                payment_intent_url = f"{settings.PAYMONGO_API_URL}/payment_intents/{payment_intent_id}"
                payment_intent_response = requests.get(payment_intent_url, headers=headers, timeout=30)
                payment_intent_data = payment_intent_response.json()
                
                return {
                    'success': True,
                    'status': 'paid',
                    'payment_intent_id': payment_intent_id,
                    'payment_method': payment_intent_data['data']['attributes']['payment_method'].get('type', 'unknown'),
                    'raw_response': response_data
                }
            elif payment_status == 'unpaid':
                return {
                    'success': False,
                    'status': 'unpaid',
                    'error': 'Payment not completed'
                }
            else:
                return {
                    'success': False,
                    'status': payment_status,
                    'error': f'Payment status: {payment_status}'
                }
        else:
            return {
                'success': False,
                'error': response_data.get('errors', 'Failed to verify payment')
            }
            
    except requests.exceptions.RequestException as e:
        return {
            'success': False,
            'error': f"Payment verification failed: {str(e)}"
        }


def process_webhook_event(payload, signature):
    """
    Process PayMongo webhook events for payment status updates.
    
    Args:
        payload (dict): The webhook payload
        signature (str): The webhook signature for verification
        
    Returns:
        dict: Processing result
    """
    try:
        # Verify webhook signature (implementation depends on PayMongo's signature method)
        # This is a placeholder for signature verification
        # In production, you should verify the signature using PAYMONGO_WEBHOOK_SECRET
        
        event_type = payload.get('data', {}).get('attributes', {}).get('type')
        payment_intent_id = payload.get('data', {}).get('id')
        
        if event_type == 'payment.paid':
            # Find payment by payment intent ID
            try:
                payment = Payment.objects.filter(paymongo_payment_id=payment_intent_id).first()
                if payment:
                    # Check if payment is already processed to prevent duplicate webhook handling
                    if payment.status == 'paid':
                        return {'success': True, 'message': 'Payment already processed'}
                    
                    payment.status = 'paid'
                    payment.save()
                    
                    # Update associated receipt and orders
                    if payment.receipt:
                        payment.receipt.reference_number = generate_order_reference_number()
                        payment.receipt.save()
                        
                        # Update orders
                        Order.objects.filter(session_id=payment.receipt.session_id).update(
                            reference_number=payment.receipt.reference_number,
                            status='confirmed'
                        )
                        
                        # Deduct stock for all ordered items
                        stock_deduction_result = deduct_stock_for_orders(
                            payment.receipt.session_id,
                            payment.id,
                            payment.user
                        )
                        
                        if not stock_deduction_result['success']:
                            # Log stock deduction failure but don't fail the payment
                            AuditLog.objects.create(
                                user=payment.user,
                                action='stock_validation_failed',
                                description=f"Stock deduction failed for payment {payment.id}: {stock_deduction_result.get('error', 'Unknown error')}",
                                ip_address=None
                            )
                    
                    # Log payment success
                    AuditLog.objects.create(
                        user=payment.user,
                        action='payment_success',
                        description=f"Payment successful for payment ID: {payment.id}",
                        ip_address=None
                    )
                    
                    return {'success': True, 'message': 'Payment processed successfully'}
                    
            except Payment.DoesNotExist:
                return {'success': False, 'error': 'Payment not found'}
                
        elif event_type == 'payment.failed':
            # Handle failed payment
            try:
                payment = Payment.objects.filter(paymongo_payment_id=payment_intent_id).first()
                if payment:
                    payment.status = 'failed'
                    payment.save()
                    
                    # Log payment failure
                    AuditLog.objects.create(
                        user=payment.user,
                        action='payment_failed',
                        description=f"Payment failed for payment ID: {payment.id}",
                        ip_address=None
                    )
                    
                    return {'success': True, 'message': 'Payment failure processed'}
                    
            except Payment.DoesNotExist:
                return {'success': False, 'error': 'Payment not found'}
        
        return {'success': True, 'message': 'Event processed'}
        
    except Exception as e:
        return {'success': False, 'error': f"Webhook processing failed: {str(e)}"}
