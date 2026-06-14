import requests
import json
import base64
from django.conf import settings
from django.utils import timezone
from bakery.models import Payment, Receipt, Order, AuditLog


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
        success_url = f"{base_url}/menu.php?payment=success"
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
