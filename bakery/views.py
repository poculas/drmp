import json
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import authenticate, login as auth_login, logout as auth_logout, update_session_auth_hash
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.views.decorators.http import require_POST
from django.contrib import messages
from django.contrib.auth.models import User
from django.contrib.auth.forms import SetPasswordForm
from django.core.paginator import Paginator
from django.utils import timezone
from django.db import models
from datetime import timedelta
from django.core.mail import send_mail
from django.template.loader import render_to_string
from django.views.decorators.csrf import csrf_exempt
import json

from bakery.models import Product, CartItem, Order, Receipt, UserProfile, AuditLog, Payment, generate_order_reference_number
from bakery.forms import SignUpForm, DeliveryForm, PickupForm, StaffCreateForm, StaffEditForm, ProductForm, OrderStatusForm
from bakery.paymongo_utils import create_paymongo_checkout, verify_paymongo_payment, process_webhook_event
from bakery.decorators import staff_required, admin_required

def send_order_confirmation_email(receipt, orders):
    """Send order confirmation email to customer"""
    try:
        subject = f"Order Confirmation - {receipt.reference_number}"
        
        # Render HTML email template
        html_message = render_to_string('emails/order_confirmation.html', {
            'receipt': receipt,
            'orders': orders
        })
        
        # Send email
        send_mail(
            subject=subject,
            message=f"Your order {receipt.reference_number} has been confirmed. Pickup availability date: {receipt.pickup_availability_date}",
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=[receipt.user.email],
            html_message=html_message,
            fail_silently=False
        )
        
        return True
    except Exception as e:
        print(f"Error sending email: {str(e)}")
        return False

def index_view(request):
    featured_products = Product.objects.all()[:3]
    gallery_products = Product.objects.all()[:6]
    return render(request, 'index.html', {
        'featured_products': featured_products,
        'gallery_products': gallery_products
    })

def aboutus_view(request):
    return render(request, 'aboutus.html')

def signup_view(request):
    if request.user.is_authenticated:
        return redirect('index')
    
    if request.method == 'POST':
        form = SignUpForm(request.POST)
        if form.is_valid():
            user = form.save(commit=False)
            user.set_password(form.cleaned_data['password'])
            user.username = form.cleaned_data['email']  # Use email as username
            user.save()
            
            UserProfile.objects.create(
                user=user,
                contactnumber=form.cleaned_data['contactnumber'],
                role='customer'  # Set default role to customer
            )
            
            # Auto log in user
            user = authenticate(username=user.username, password=form.cleaned_data['password'])
            if user is not None:
                auth_login(request, user)
            
            messages.success(request, "Signup successful!")
            return redirect('index')
        else:
            errors = []
            for field, field_errors in form.errors.items():
                for error in field_errors:
                    errors.append(error)
            error_msg = " ".join(errors)
            messages.error(request, error_msg)
    else:
        form = SignUpForm()
    
    return render(request, 'signup.html', {'form': form})

def login_view(request):
    if request.user.is_authenticated:
        # Redirect based on role
        if request.user.is_superuser:
            return redirect('/admin/')
        elif hasattr(request.user, 'profile'):
            if request.user.profile.role == 'staff':
                return redirect('staff_dashboard')
            elif request.user.profile.role == 'customer':
                return redirect('index')
        return redirect('index')
    
    if request.method == 'POST':
        email = request.POST.get('email')
        password = request.POST.get('password')
        
        user = authenticate(request, username=email, password=password)
        if user is not None:
            auth_login(request, user)
            messages.success(request, "Login successful!")
            
            # Redirect based on role
            if user.is_superuser:
                return redirect('/admin/')
            elif hasattr(user, 'profile'):
                if user.profile.role == 'staff':
                    return redirect('staff_dashboard')
                elif user.profile.role == 'customer':
                    return redirect('index')
            return redirect('index')
        else:
            messages.error(request, "Incorrect Username or Password!")
            
    return render(request, 'login.html')

def logout_view(request):
    if request.user.is_authenticated:
        auth_logout(request)
    return redirect('index')

def menu_view(request):
    # Check for payment status from PayMongo redirect
    payment_status = request.GET.get('payment')
    if payment_status == 'success':
        messages.success(request, 'Payment successful! Please check your email for confirmation.')
    elif payment_status == 'failed':
        messages.error(request, 'Payment failed. Please try again.')
    
    products = Product.objects.filter(is_available=True)
    paginator = Paginator(products, 12)
    page_number = request.GET.get('page', 1)
    page_obj = paginator.get_page(page_number)
    return render(request, 'menu.html', {'page_obj': page_obj, 'products': page_obj})

@login_required
def cart_get(request):
    cart_items = CartItem.objects.filter(user=request.user)
    items = []
    total_price = 0.00
    for item in cart_items:
        subtotal = float(item.product.price) * item.quantity
        items.append({
            'item_name': item.product.name,
            'item_price': float(item.product.price),
            'quantity': item.quantity,
            'subtotal': subtotal
        })
        total_price += subtotal
    
    request.session['total_price'] = str(total_price)
    return JsonResponse({'items': items, 'total_price': total_price})

@login_required
@require_POST
def cart_add(request):
    try:
        data = json.loads(request.body)
        name = data.get('name')
        quantity = int(data.get('quantity', 1))
        product = get_object_or_404(Product, name=name)
        
        # Validation constants
        MAX_PER_PRODUCT = 5
        MAX_CART_CAPACITY = 15
        
        # Stock availability validation
        if not product.is_available or product.stock <= 0:
            AuditLog.objects.create(
                user=request.user,
                action='stock_validation_failed',
                description=f"Attempted to add out-of-stock product: {product.name}",
                ip_address=request.META.get('REMOTE_ADDR')
            )
            return JsonResponse({'message': 'Product is out of stock'}, status=400)
        
        # Check if cart item already exists
        cart_item = CartItem.objects.filter(user=request.user, product=product).first()
        created = cart_item is None
        
        # Calculate new quantity
        new_quantity = cart_item.quantity + quantity if not created else quantity
        
        # Per-product purchase limit validation
        if new_quantity > MAX_PER_PRODUCT:
            AuditLog.objects.create(
                user=request.user,
                action='per_product_limit_failed',
                description=f"Attempted to add {new_quantity} units of {product.name} (max {MAX_PER_PRODUCT})",
                ip_address=request.META.get('REMOTE_ADDR')
            )
            return JsonResponse({'message': f'Maximum {MAX_PER_PRODUCT} units per product allowed'}, status=400)
        
        # Stock availability validation for requested quantity
        if new_quantity > product.stock:
            AuditLog.objects.create(
                user=request.user,
                action='stock_validation_failed',
                description=f"Requested {new_quantity} units of {product.name} exceeds available stock ({product.stock})",
                ip_address=request.META.get('REMOTE_ADDR')
            )
            return JsonResponse({'message': 'Requested quantity exceeds available stock'}, status=400)
        
        # Cart capacity limit validation
        current_cart_total = CartItem.objects.filter(user=request.user).aggregate(
            total=models.Sum('quantity')
        )['total'] or 0
        if not created:
            current_cart_total -= cart_item.quantity  # Subtract current item quantity before adding new quantity
        
        if current_cart_total + quantity > MAX_CART_CAPACITY:
            AuditLog.objects.create(
                user=request.user,
                action='cart_capacity_failed',
                description=f"Attempted to add {quantity} items (cart total would be {current_cart_total + quantity}, max {MAX_CART_CAPACITY})",
                ip_address=request.META.get('REMOTE_ADDR')
            )
            return JsonResponse({'message': f'Cart capacity exceeded. Maximum {MAX_CART_CAPACITY} items allowed'}, status=400)
        
        # Create or update cart item (only after all validations pass)
        if created:
            cart_item = CartItem.objects.create(user=request.user, product=product, quantity=quantity)
        else:
            cart_item.quantity = new_quantity
            cart_item.save()
            
        return JsonResponse({'message': 'Item added to cart'})
    except Exception as e:
        AuditLog.objects.create(
            user=request.user,
            action='cart_add_error',
            description=f"Error adding item to cart: {str(e)}",
            ip_address=request.META.get('REMOTE_ADDR')
        )
        return JsonResponse({'message': f'Error adding item to cart: {str(e)}'}, status=400)

@login_required
@require_POST
def cart_remove(request):
    try:
        data = json.loads(request.body)
        index = data.get('index')
        action = data.get('action', 'decrement')
        
        cart_items = list(CartItem.objects.filter(user=request.user).order_by('id'))
        
        if 0 <= index < len(cart_items):
            item_to_remove = cart_items[index]
            
            if action == 'remove':
                # Actually remove the item from cart
                item_to_remove.delete()
                return JsonResponse({'message': 'Item removed from cart'})
            else:
                # Decrement quantity (old behavior)
                if item_to_remove.quantity > 1:
                    item_to_remove.quantity -= 1
                    item_to_remove.save()
                    return JsonResponse({'message': 'Item quantity reduced'})
                else:
                    item_to_remove.delete()
                    return JsonResponse({'message': 'Item removed from cart'})
        else:
            return JsonResponse({'message': 'Item not found in cart'}, status=404)
    except Exception as e:
        return JsonResponse({'message': f'Error removing item from cart: {str(e)}'}, status=400)

@login_required
@require_POST
def cart_update_quantity(request):
    try:
        data = json.loads(request.body)
        index = data.get('index')
        action = data.get('action')
        
        # Validation constants
        MAX_PER_PRODUCT = 5
        MAX_CART_CAPACITY = 15
        
        cart_items = list(CartItem.objects.filter(user=request.user).order_by('id'))
        
        if 0 <= index < len(cart_items):
            cart_item = cart_items[index]
            
            if action == 'increment':
                # Check per-product limit
                if cart_item.quantity >= MAX_PER_PRODUCT:
                    return JsonResponse({'success': False, 'message': f'Maximum {MAX_PER_PRODUCT} units per product allowed'})
                
                # Check stock availability
                if cart_item.quantity >= cart_item.product.stock:
                    return JsonResponse({'success': False, 'message': 'Requested quantity exceeds available stock'})
                
                # Check cart capacity
                current_cart_total = CartItem.objects.filter(user=request.user).aggregate(
                    total=models.Sum('quantity')
                )['total'] or 0
                if current_cart_total >= MAX_CART_CAPACITY:
                    return JsonResponse({'success': False, 'message': f'Cart capacity exceeded. Maximum {MAX_CART_CAPACITY} items allowed'})
                
                # Increment quantity
                cart_item.quantity += 1
                cart_item.save()
                return JsonResponse({'success': True, 'message': 'Item quantity increased'})
                
            elif action == 'decrement':
                if cart_item.quantity > 1:
                    cart_item.quantity -= 1
                    cart_item.save()
                    return JsonResponse({'success': True, 'message': 'Item quantity reduced'})
                else:
                    return JsonResponse({'success': False, 'message': 'Cannot reduce quantity below 1. Use X to remove item.'})
            else:
                return JsonResponse({'success': False, 'message': 'Invalid action'}, status=400)
        else:
            return JsonResponse({'success': False, 'message': 'Item not found in cart'}, status=404)
    except Exception as e:
        return JsonResponse({'success': False, 'message': f'Error updating item quantity: {str(e)}'}, status=400)

@login_required
@require_POST
def checkout_view(request):
    cart_items = CartItem.objects.filter(user=request.user)
    if not cart_items.exists():
        return JsonResponse({'success': False, 'message': 'You need to add an item first!'})
    
    # Validation constants
    MAX_PER_PRODUCT = 5
    ORDER_COOLDOWN_MINUTES = 5
    MAX_DAILY_ORDERS = 3
    
    # Order cooldown validation
    last_order = Order.objects.filter(user=request.user).order_by('-ordered_at').first()
    if last_order:
        time_since_last_order = timezone.now() - last_order.ordered_at
        if time_since_last_order < timedelta(minutes=ORDER_COOLDOWN_MINUTES):
            remaining_minutes = ORDER_COOLDOWN_MINUTES - (time_since_last_order.seconds // 60)
            AuditLog.objects.create(
                user=request.user,
                action='order_cooldown_failed',
                description=f"Attempted checkout during cooldown period. Wait {remaining_minutes} more minutes.",
                ip_address=request.META.get('REMOTE_ADDR')
            )
            return JsonResponse({'success': False, 'message': f'Please wait {remaining_minutes} minutes before placing another order'}, status=429)
    
    # Daily order limit validation
    today = timezone.now().date()
    daily_orders = Order.objects.filter(user=request.user, ordered_at__date=today).count()
    if daily_orders >= MAX_DAILY_ORDERS:
        AuditLog.objects.create(
            user=request.user,
            action='daily_order_limit_failed',
            description=f"Attempted checkout with {daily_orders} orders today (max {MAX_DAILY_ORDERS})",
            ip_address=request.META.get('REMOTE_ADDR')
        )
        return JsonResponse({'success': False, 'message': f'Daily order limit of {MAX_DAILY_ORDERS} orders reached'}, status=429)
    
    # Stock and per-product validation
    for item in cart_items:
        # Stock availability validation
        if not item.product.is_available or item.product.stock <= 0:
            AuditLog.objects.create(
                user=request.user,
                action='stock_validation_failed',
                description=f"Checkout failed: {item.product.name} is out of stock",
                ip_address=request.META.get('REMOTE_ADDR')
            )
            return JsonResponse({'success': False, 'message': f'{item.product.name} is out of stock'}, status=400)
        
        # Stock quantity validation
        if item.quantity > item.product.stock:
            AuditLog.objects.create(
                user=request.user,
                action='stock_validation_failed',
                description=f"Checkout failed: Requested {item.quantity} units of {item.product.name} exceeds available stock ({item.product.stock})",
                ip_address=request.META.get('REMOTE_ADDR')
            )
            return JsonResponse({'success': False, 'message': f'Insufficient stock for {item.product.name}'}, status=400)
        
        # Per-product purchase limit validation
        if item.quantity > MAX_PER_PRODUCT:
            AuditLog.objects.create(
                user=request.user,
                action='per_product_limit_failed',
                description=f"Checkout failed: {item.quantity} units of {item.product.name} exceeds maximum {MAX_PER_PRODUCT}",
                ip_address=request.META.get('REMOTE_ADDR')
            )
            return JsonResponse({'success': False, 'message': f'Exceeds maximum {MAX_PER_PRODUCT} units for {item.product.name}'}, status=400)
        
    session_id = request.session.session_key
    if not session_id:
        request.session.create()
        session_id = request.session.session_key
        
    request.session['checkout_session_id'] = session_id
    
    total_price = 0.00
    for item in cart_items:
        subtotal = item.product.price * item.quantity
        total_price += float(subtotal)
        
        # Update stock
        item.product.stock -= item.quantity
        if item.product.stock <= 0:
            item.product.is_available = False
        item.product.save()
        
        for _ in range(item.quantity):
            Order.objects.create(
                user=request.user,
                session_id=session_id,
                item_name=item.product.name,
                item_price=item.product.price
            )
            
    request.session['total_price'] = str(total_price)
    cart_items.delete()
    
    return JsonResponse({'success': True})

@login_required
def pickup_view(request):
    session_id = request.session.get('checkout_session_id')
    total_price = request.session.get('total_price', '0.00')
    
    if not session_id or not Order.objects.filter(session_id=session_id).exists():
        messages.error(request, "No active order to bill.")
        return redirect('menu')
    
    orders = Order.objects.filter(session_id=session_id, user=request.user)
        
    if request.method == 'POST':
        form = PickupForm(request.POST, user=request.user)
        if form.is_valid():
            # Calculate payment amounts based on payment option
            payment_option = form.cleaned_data['payment_option']
            total_amount = float(total_price)
            
            if payment_option == 'full':
                amount_paid = total_amount
                remaining_balance = 0
            else:  # partial
                amount_paid = total_amount * 0.5
                remaining_balance = total_amount - amount_paid
            
            # Calculate pickup availability date (3 days from now)
            pickup_availability_date = timezone.now().date() + timedelta(days=3)
            
            # Store checkout information in session for payment processing
            request.session['checkout_info'] = {
                'full_name': form.cleaned_data['full_name'],
                'contact_number': form.cleaned_data['contact_number'],
                'payment_method': form.cleaned_data['payment_method'],
                'payment_option': payment_option,
                'total_amount': total_amount,
                'amount_paid': amount_paid,
                'remaining_balance': remaining_balance,
                'pickup_availability_date': pickup_availability_date.strftime('%Y-%m-%d')
            }
            
            # Create PayMongo checkout session
            payment_result = create_paymongo_checkout(
                amount=amount_paid,
                description=f"Order Payment - {payment_option.title()} - {request.user.username}",
                user=request.user
            )
            
            if payment_result['success']:
                # Store payment ID in session
                request.session['payment_id'] = payment_result['payment_id']
                request.session['checkout_id'] = payment_result['checkout_id']
                
                # Redirect to PayMongo checkout
                return redirect(payment_result['checkout_url'])
            else:
                messages.error(request, f"Payment initialization failed: {payment_result['error']}")
                return render(request, 'pickup.html', {
                    'form': form,
                    'total_price': total_price,
                    'orders': orders
                })
        else:
            messages.error(request, "Invalid form data. Please verify all inputs.")
    else:
        form = PickupForm(user=request.user)
        
    return render(request, 'pickup.html', {
        'form': form,
        'total_price': total_price,
        'orders': orders
    })

@login_required
def payment_success_view(request):
    """Handle PayMongo payment success callback"""
    checkout_id = request.GET.get('checkout_id')
    payment_id = request.session.get('payment_id')
    checkout_info = request.session.get('checkout_info')
    session_id = request.session.get('checkout_session_id')
    
    if not checkout_id or not payment_id or not checkout_info or not session_id:
        messages.error(request, "Invalid payment session. Please try again.")
        return redirect('menu')
    
    # Verify payment with PayMongo
    verification_result = verify_paymongo_payment(checkout_id)
    
    if verification_result['success'] and verification_result['status'] == 'paid':
        try:
            # Update payment record
            payment = Payment.objects.get(id=payment_id)
            payment.status = 'paid'
            payment.paymongo_payment_id = verification_result.get('payment_intent_id')
            payment.payment_method = verification_result.get('payment_method')
            payment.raw_response = verification_result.get('raw_response')
            payment.save()
            
            # Generate order reference number
            reference_number = generate_order_reference_number()
            
            # Create receipt with payment information
            receipt = Receipt.objects.create(
                user=request.user,
                session_id=session_id,
                total_price=checkout_info['total_amount'],
                full_name=checkout_info['full_name'],
                contact_number=checkout_info['contact_number'],
                reference_number=reference_number,
                payment_option=checkout_info['payment_option'],
                total_amount=checkout_info['total_amount'],
                amount_paid=checkout_info['amount_paid'],
                remaining_balance=checkout_info['remaining_balance'],
                pickup_availability_date=timezone.datetime.strptime(checkout_info['pickup_availability_date'], '%Y-%m-%d').date()
            )
            
            # Link payment to receipt
            payment.receipt = receipt
            payment.save()
            
            # Update orders with payment information and reference number
            orders = Order.objects.filter(session_id=session_id, user=request.user)
            orders.update(
                payment_option=checkout_info['payment_option'],
                total_amount=checkout_info['total_amount'],
                amount_paid=checkout_info['amount_paid'],
                remaining_balance=checkout_info['remaining_balance'],
                pickup_availability_date=timezone.datetime.strptime(checkout_info['pickup_availability_date'], '%Y-%m-%d').date(),
                reference_number=reference_number,
                status='confirmed'
            )
            
            # Log payment success
            AuditLog.objects.create(
                user=request.user,
                action='payment_success',
                description=f"Payment successful for order {reference_number}, amount: ₱{checkout_info['amount_paid']}",
                ip_address=request.META.get('REMOTE_ADDR')
            )
            
            # Send confirmation email
            send_order_confirmation_email(receipt, orders)
            
            # Clear session data
            request.session.pop('payment_id', None)
            request.session.pop('checkout_id', None)
            request.session.pop('checkout_info', None)
            
            return redirect('order_success')
            
        except Exception as e:
            messages.error(request, f"Error processing order: {str(e)}")
            AuditLog.objects.create(
                user=request.user,
                action='payment_verification_failed',
                description=f"Error processing order after payment: {str(e)}",
                ip_address=request.META.get('REMOTE_ADDR')
            )
            return redirect('menu')
    else:
        # Payment failed or verification failed
        messages.error(request, f"Payment verification failed: {verification_result.get('error', 'Unknown error')}")
        
        # Update payment record to failed
        try:
            payment = Payment.objects.get(id=payment_id)
            payment.status = 'failed'
            payment.save()
            
            AuditLog.objects.create(
                user=request.user,
                action='payment_failed',
                description=f"Payment verification failed: {verification_result.get('error')}",
                ip_address=request.META.get('REMOTE_ADDR')
            )
        except Payment.DoesNotExist:
            pass
        
        return redirect('menu')

@csrf_exempt
def paymongo_webhook_view(request):
    """Handle PayMongo webhook events for payment status updates"""
    if request.method != 'POST':
        return JsonResponse({'success': False, 'error': 'Method not allowed'}, status=405)
    
    try:
        payload = json.loads(request.body)
        signature = request.headers.get('X-Paymongo-Signature', '')
        
        # Process the webhook event
        result = process_webhook_event(payload, signature)
        
        if result['success']:
            return JsonResponse({'success': True})
        else:
            return JsonResponse({'success': False, 'error': result['error']}, status=400)
            
    except json.JSONDecodeError:
        return JsonResponse({'success': False, 'error': 'Invalid JSON payload'}, status=400)
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)}, status=500)

@login_required
def order_success_view(request):
    """Display order success page after successful payment"""
    # Get the most recent receipt for the user
    receipt = Receipt.objects.filter(user=request.user).order_by('-id').first()
    
    if not receipt:
        messages.error(request, "No order found.")
        return redirect('menu')
    
    orders = Order.objects.filter(session_id=receipt.session_id, user=request.user)
    
    return render(request, 'order_success.html', {
        'receipt': receipt,
        'orders': orders
    })

@login_required
def receipt_view(request):
    session_id = request.session.get('checkout_session_id')
    if not session_id:
        return redirect('menu')
        
    receipt = get_object_or_404(Receipt, session_id=session_id, user=request.user)
    orders = Order.objects.filter(session_id=session_id, user=request.user)
    
    profile = getattr(request.user, 'profile', None)
    contact_number = profile.contactnumber if profile else 'Not Provided'
    
    return render(request, 'receipt.html', {
        'receipt': receipt,
        'orders': orders,
        'contact_number': contact_number
    })

@login_required
def set_password_view(request):
    if request.method == 'POST':
        form = SetPasswordForm(request.user, request.POST)
        if form.is_valid():
            form.save()
            update_session_auth_hash(request, form.user)
            messages.success(request, "Password set successfully! You can now log in using your email and password.")
            return redirect('index')
    else:
        form = SetPasswordForm(request.user)
    
    return render(request, 'set_password.html', {'form': form})

# Staff Dashboard Views
@staff_required
def staff_dashboard(request):
    # Get statistics
    total_products = Product.objects.count()
    total_orders = Order.objects.count()
    pending_orders = Order.objects.filter(status='pending').count()
    confirmed_orders = Order.objects.filter(status='confirmed').count()
    ready_orders = Order.objects.filter(status='ready').count()
    completed_orders = Order.objects.filter(status='completed').count()
    
    context = {
        'total_products': total_products,
        'total_orders': total_orders,
        'pending_orders': pending_orders,
        'confirmed_orders': confirmed_orders,
        'ready_orders': ready_orders,
        'completed_orders': completed_orders,
    }
    return render(request, 'staff/dashboard.html', context)

@staff_required
def staff_products(request):
    products = Product.objects.all().order_by('name')
    paginator = Paginator(products, 10)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    return render(request, 'staff/products.html', {'page_obj': page_obj})

@staff_required
def staff_product_create(request):
    if request.method == 'POST':
        form = ProductForm(request.POST)
        if form.is_valid():
            product = form.save()
            # Log audit
            AuditLog.objects.create(
                user=request.user,
                action='product_create',
                description=f"Created product: {product.name}",
                product_id=product.id,
                ip_address=request.META.get('REMOTE_ADDR')
            )
            messages.success(request, "Product created successfully!")
            return redirect('staff_products')
    else:
        form = ProductForm()
    
    return render(request, 'staff/product_form.html', {'form': form, 'title': 'Add Product'})

@staff_required
def staff_product_edit(request, product_id):
    product = get_object_or_404(Product, id=product_id)
    
    if request.method == 'POST':
        # Handle image upload separately
        form_data = request.POST.copy()
        if 'image' not in request.FILES:
            # Keep existing image if no new image uploaded
            form_data['image'] = product.image
        form = ProductForm(form_data, request.FILES, instance=product)
        if form.is_valid():
            form.save()
            # Log audit
            AuditLog.objects.create(
                user=request.user,
                action='product_edit',
                description=f"Edited product: {product.name}",
                product_id=product.id,
                ip_address=request.META.get('REMOTE_ADDR')
            )
            messages.success(request, "Product updated successfully!")
            return redirect('staff_products')
    else:
        form = ProductForm(instance=product)
    
    return render(request, 'staff/product_form.html', {'form': form, 'title': 'Edit Product', 'product': product})

@staff_required
def staff_product_delete(request, product_id):
    product = get_object_or_404(Product, id=product_id)
    
    if request.method == 'POST':
        product_name = product.name
        product.delete()
        # Log audit
        AuditLog.objects.create(
            user=request.user,
            action='product_delete',
            description=f"Deleted product: {product_name}",
            product_id=product_id,
            ip_address=request.META.get('REMOTE_ADDR')
        )
        messages.success(request, "Product deleted successfully!")
        return redirect('staff_products')
    
    return render(request, 'staff/product_confirm_delete.html', {'product': product})

@staff_required
def staff_orders(request):
    orders = Order.objects.all().select_related('user').order_by('-ordered_at')
    paginator = Paginator(orders, 10)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    return render(request, 'staff/orders.html', {'page_obj': page_obj})

@staff_required
def staff_order_detail(request, order_id):
    order = get_object_or_404(Order, id=order_id)
    
    if request.method == 'POST':
        form = OrderStatusForm(request.POST, instance=order)
        if form.is_valid():
            old_status = order.status
            form.save()
            # Log audit
            AuditLog.objects.create(
                user=request.user,
                action='order_status_update',
                description=f"Updated order {order.id} status from {old_status} to {order.status}",
                order_id=order.id,
                ip_address=request.META.get('REMOTE_ADDR')
            )
            messages.success(request, "Order status updated successfully!")
            return redirect('staff_orders')
    else:
        form = OrderStatusForm(instance=order)
    
    return render(request, 'staff/order_detail.html', {'order': order, 'form': form})

# Admin Views for Staff Management
@admin_required
def admin_staff_list(request):
    staff_users = User.objects.filter(profile__role='staff').select_related('profile')
    
    return render(request, 'admin/staff_list.html', {'staff_users': staff_users})

@admin_required
def admin_staff_create(request):
    if request.method == 'POST':
        form = StaffCreateForm(request.POST)
        if form.is_valid():
            user = form.save()
            # Log audit
            AuditLog.objects.create(
                user=request.user,
                action='staff_create',
                description=f"Created staff account: {user.email}",
                target_user_id=user.id,
                ip_address=request.META.get('REMOTE_ADDR')
            )
            messages.success(request, "Staff account created successfully!")
            return redirect('admin_staff_list')
    else:
        form = StaffCreateForm()
    
    return render(request, 'admin/staff_form.html', {'form': form, 'title': 'Create Staff Account'})

@admin_required
def admin_staff_edit(request, user_id):
    user = get_object_or_404(User, id=user_id, profile__role='staff')
    
    if request.method == 'POST':
        form = StaffEditForm(request.POST, instance=user)
        if form.is_valid():
            old_active = user.profile.is_active
            form.save()
            # Log audit
            action = 'staff_activate' if form.cleaned_data['is_active'] and not old_active else 'staff_deactivate'
            if old_active != form.cleaned_data['is_active']:
                AuditLog.objects.create(
                    user=request.user,
                    action=action,
                    description=f"{'Activated' if form.cleaned_data['is_active'] else 'Deactivated'} staff account: {user.email}",
                    target_user_id=user.id,
                    ip_address=request.META.get('REMOTE_ADDR')
                )
            messages.success(request, "Staff account updated successfully!")
            return redirect('admin_staff_list')
    else:
        form = StaffEditForm(instance=user)
    
    return render(request, 'admin/staff_form.html', {'form': form, 'title': 'Edit Staff Account', 'user': user})

@admin_required
def admin_staff_delete(request, user_id):
    user = get_object_or_404(User, id=user_id, profile__role='staff')
    
    if request.method == 'POST':
        user_email = user.email
        user.delete()
        # Log audit
        AuditLog.objects.create(
            user=request.user,
            action='staff_deactivate',
            description=f"Deleted staff account: {user_email}",
            target_user_id=user_id,
            ip_address=request.META.get('REMOTE_ADDR')
        )
        messages.success(request, "Staff account deleted successfully!")
        return redirect('admin_staff_list')
    
    return render(request, 'admin/staff_confirm_delete.html', {'user': user})
