import json
import logging
import random
import string

from allauth.socialaccount.models import SocialLogin
from allauth.socialaccount.helpers import complete_social_login

from collections import defaultdict
from decimal import Decimal

from dough_re_mi import settings

logger = logging.getLogger('security')
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import authenticate, login as auth_login, logout as auth_logout, update_session_auth_hash
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse, HttpResponse, HttpResponseRedirect
from django.views.decorators.http import require_POST
from django.views.decorators.csrf import ensure_csrf_cookie, csrf_exempt
from django.contrib import messages
from django.contrib.auth.models import User
from django.core.paginator import Paginator
from django.urls import reverse
from django.contrib.auth.forms import SetPasswordForm, PasswordChangeForm
from django.core.mail import send_mail, EmailMultiAlternatives
from django.utils import timezone
from datetime import timedelta
from django.core.cache import cache
from django.core.exceptions import ObjectDoesNotExist
from django.db import models
from django.template.loader import render_to_string

from bakery.models import Product, CartItem, Order, Receipt, UserProfile, AuditLog, Payment, generate_order_reference_number, MFACode, TOTPSecret
from bakery.order_views import order_detail_view
from bakery.forms import SignUpForm, DeliveryForm, PickupForm, StaffCreateForm, StaffEditForm, ProductForm, OrderStatusForm, EmailChangeForm
from bakery.paymongo_utils import create_paymongo_checkout, verify_paymongo_payment, deduct_stock_for_orders, process_webhook_event
from bakery.decorators import staff_required, admin_required
from bakery.signals import get_client_ip
from bakery.utils import generate_captcha_svg

def link_account_prompt(request):
    """Show prompt asking user to confirm linking their Google account."""
    email = request.session.get('link_email')
    if not email:
        return redirect('login')

    if request.method == 'POST':
        if 'confirm' in request.POST:
            # User confirmed — deserialize and complete the social login
            serialized = request.session.get('pending_sociallogin')
            if serialized:
                sociallogin = SocialLogin.deserialize(serialized)
                # Connect to existing user
                try:
                    existing_user = User.objects.get(email__iexact=email)
                    sociallogin.connect(request, existing_user)
                    from django.contrib.auth import login as auth_login
                    auth_login(request, existing_user,
                               backend='allauth.account.auth_backends.AuthenticationBackend')
                    # Clean up session
                    del request.session['pending_sociallogin']
                    del request.session['link_email']
                    return redirect('index')
                except User.DoesNotExist:
                    pass
        # User declined — redirect to login
        request.session.pop('pending_sociallogin', None)
        request.session.pop('link_email', None)
        return redirect('login')

    return render(request, 'link_account_prompt.html', {'email': email})

# ============================================================================
# 2FA Helper Functions
# ============================================================================

def generate_mfa_code(length=6):
    """Generate a random 6-digit code"""
    return ''.join(random.choices(string.digits, k=length))

def send_mfa_code_via_email(user, code):
    """Send MFA code via email"""
    try:
        subject = "Your 2FA Verification Code - Dough Re Mi Patisserie"
        message = f"""
Dear {user.first_name or user.username},

Your 2FA verification code is: {code}

This code will expire in 2 minutes.

If you did not request this code, please ignore this email.

Best regards,
Dough Re Mi Patisserie Team
        """
        send_mail(
            subject,
            message,
            settings.EMAIL_HOST_USER,
            [user.email],
            fail_silently=False,
        )
        return True
    except Exception as e:
        print(f"Email sending failed: {str(e)}")
        return False

def create_mfa_code(user):
    """Create and send MFA code via email only"""
    # Delete existing code
    MFACode.objects.filter(user=user).delete()
    
    code = generate_mfa_code()
    expires_at = timezone.now() + timedelta(minutes=2)
    
    mfa_obj = MFACode.objects.create(
        user=user,
        code=code,
        method='email',
        expires_at=expires_at,
        attempts=0,
        verified_at=None
    )
    
    send_mfa_code_via_email(user, code)
    return mfa_obj

def captcha_image_view(request):
    """Generates a random CAPTCHA code, saves it in session, and returns SVG image response."""
    chars = "ABCDEFGHJKLMNPQRSTUVWXYZ23456789"
    code = "".join(random.choices(chars, k=5))
    request.session['captcha_code'] = code
    svg_content = generate_captcha_svg(code)
    return HttpResponse(svg_content, content_type="image/svg+xml")

def send_order_confirmation_email(receipt, orders):
    """Send order confirmation email to customer"""
    try:
        subject = f"Order Confirmation - {receipt.reference_number}"
        from_email = settings.DEFAULT_FROM_EMAIL or settings.EMAIL_HOST_USER
        if not from_email:
            raise ValueError('No from email configured for order confirmation email.')

        # Build order item details for the email receipt
        order_items = []
        total_quantity = 0
        subtotal = Decimal('0.00')
        for order in orders:
            quantity = order.quantity or 1
            line_total = order.item_price * quantity
            order_items.append({
                'name': order.item_name,
                'quantity': quantity,
                'unit_price': order.item_price,
                'line_total': line_total,
            })
            total_quantity += quantity
            subtotal += line_total

        # Render HTML email template
        html_message = render_to_string('emails/order_confirmation.html', {
            'receipt': receipt,
            'orders': order_items,
            'total_quantity': total_quantity,
            'subtotal': subtotal,
            'settings': settings
        })

        plain_message = (
            f"Order {receipt.reference_number} confirmed. "
            f"Amount paid: ₱{receipt.amount_paid}. "
            f"Pickup date: {receipt.pickup_availability_date}. "
            f"Thank you for ordering from Dough Re Mi Patisserie."
        )

        email = EmailMultiAlternatives(
            subject=subject,
            body=plain_message,
            from_email=from_email,
            to=[receipt.user.email]
        )
        email.attach_alternative(html_message, "text/html")
        email.send(fail_silently=False)

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
        # Rate limiting: Check IP-based signup rate limit (max 5 attempts per 15 minutes)
        client_ip = get_client_ip(request)
        rate_limit_key = f'signup_rate_limit_{client_ip}'
        attempts = cache.get(rate_limit_key, 0)

        if attempts >= 5:
            messages.error(request, "Too many signup attempts. Please try again later.")
            logger.warning(f"SIGNUP_RATE_LIMIT | IP: {client_ip} | Attempts: {attempts}")
            return render(request, 'signup.html', {'form': SignUpForm(request.POST), 'rate_limited': True})

        # Increment rate limit counter
        cache.set(rate_limit_key, attempts + 1, 900)  # 15 minutes

        # CAPTCHA validation
        captcha_submitted = request.POST.get('captcha', '').strip().upper()
        captcha_expected = request.session.get('captcha_code')

        # Clear session CAPTCHA to prevent replay/reuse
        if 'captcha_code' in request.session:
            del request.session['captcha_code']

        if not captcha_expected or captcha_submitted != captcha_expected:
            messages.error(request, "Invalid CAPTCHA. Please try again.")
            logger.warning(f"SIGNUP_FAILED | IP: {client_ip} | Reason: Invalid CAPTCHA | Expected: {captcha_expected}, Submitted: {captcha_submitted}")
            return render(request, 'signup.html', {'form': SignUpForm(request.POST)})

        form = SignUpForm(request.POST)
        if form.is_valid():
            user = form.save(commit=False)
            user.set_password(form.cleaned_data['password'])
            user.username = form.cleaned_data['email']  # Use email as username
            user.save()
            
            UserProfile.objects.update_or_create(
                user=user,
                defaults={
                    'contactnumber': form.cleaned_data['contactnumber'],
                    'role': 'customer'  # Set default role to customer
                }
            )
            
            logger.info(f"SIGNUP_SUCCESS | IP: {client_ip} | User: {user.email}")
            
            # Auto log in user
            user = authenticate(username=user.username, password=form.cleaned_data['password'])
            if user is not None:
                auth_login(request, user)
                logger.info(f"LOGIN_SUCCESS | IP: {client_ip} | User: {user.email} (Auto-login after signup)")
            
            messages.success(request, "Signup successful!")
            return redirect('index')
        else:
            errors = []
            for field, field_errors in form.errors.items():
                for error in field_errors:
                    errors.append(error)
            error_msg = " ".join(errors)
            logger.warning(f"SIGNUP_FAILED | IP: {client_ip} | Reason: Form validation errors: {error_msg}")
            messages.error(request, error_msg)
    else:
        form = SignUpForm()
    
    return render(request, 'signup.html', {'form': form})

def login_view(request):
    if request.user.is_authenticated:
        # Redirect based on role, but check if this is a redirect from @login_required
        # If there's a 'next' parameter, it means user was trying to access a protected page
        next_url = request.GET.get('next')
        if next_url:
            # Allow the user to continue to their intended destination
            return redirect(next_url)
        
        # Otherwise, redirect based on role
        if request.user.is_superuser:
            return redirect('/admin/')
        elif hasattr(request.user, 'profile'):
            if request.user.profile.role == 'staff':
                return redirect('staff_dashboard')
            elif request.user.profile.role == 'customer':
                return redirect('index')
        return redirect('index')

    context = {}
    if request.method == 'POST':
        client_ip = get_client_ip(request)
        # CAPTCHA validation
        captcha_submitted = request.POST.get('captcha', '').strip().upper()
        captcha_expected = request.session.get('captcha_code')

        # Clear session CAPTCHA to prevent replay/reuse
        if 'captcha_code' in request.session:
            del request.session['captcha_code']

        if not captcha_expected or captcha_submitted != captcha_expected:
            messages.error(request, "Invalid CAPTCHA. Please try again.")
            logger.warning(f"LOGIN_FAILED | IP: {client_ip} | Reason: Invalid CAPTCHA")
            context['email'] = request.POST.get('email', '')
            return render(request, 'login.html', context)

        email = request.POST.get('email')
        password = request.POST.get('password')

        # Rate limiting: Check IP-based rate limit (max 10 attempts per 15 minutes)
        rate_limit_key = f'login_rate_limit_{client_ip}'
        attempts = cache.get(rate_limit_key, 0)

        if attempts >= 10:
            messages.error(request, "Too many login attempts. Please try again later.")
            logger.warning(f"LOGIN_RATE_LIMIT | IP: {client_ip} | Attempts: {attempts}")
            context['email'] = request.POST.get('email', '')
            context['rate_limited'] = True
            return render(request, 'login.html', context)

        # Increment rate limit counter
        cache.set(rate_limit_key, attempts + 1, 900)  # 15 minutes

        user = authenticate(request, username=email, password=password)
        if user is not None:
            # Check if account is locked
            try:
                profile = user.profile
                if profile.is_locked():
                    remaining_time = profile.lockout_until - timezone.now()
                    seconds = int(remaining_time.total_seconds())
                    minutes = int(seconds / 60)
                    messages.error(request, f"Account is locked. Please try again in {minutes} minutes.")
                    context['lockout_seconds'] = seconds
                    context['email'] = email
                    logger.warning(f"LOGIN_LOCKED | IP: {client_ip} | User: {user.email}")
                    return render(request, 'login.html', context)

                # Reset failed attempts on successful authentication
                profile.reset_failed_attempts()
                
                # Staff should always use MFA; other users use it when enabled
                if profile.role == 'staff' or profile.mfa_email_enabled:
                    create_mfa_code(user)
                    request.session['mfa_user_id'] = user.id
                    request.session['mfa_method'] = 'email'
                    messages.info(request, "Verification code sent to your email.")
                    logger.info(f"LOGIN_MFA_CHALLENGE | IP: {client_ip} | User: {user.email}")
                    return redirect('verify_mfa')
            except UserProfile.DoesNotExist:
                # Create profile if it doesn't exist
                UserProfile.objects.get_or_create(
                    user=user,
                    defaults={'contactnumber': '', 'role': 'customer'}
                )
            
            # No 2FA or profile doesn't exist, log in normally
            auth_login(request, user)
            messages.success(request, "Login successful!")
            logger.info(f"LOGIN_SUCCESS | IP: {client_ip} | User: {user.email}")
            
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
            # Failed login attempt - increment counter for the user if exists
            logger.warning(f"LOGIN_FAILED | IP: {client_ip} | Reason: Invalid credentials | Email: {email}")
            context['email'] = email
            try:
                user_obj = User.objects.get(username=email)
                profile = user_obj.profile
                profile.increment_failed_attempts()

                if profile.is_locked():
                    messages.error(request, "Account locked due to too many failed attempts. Please try again in 30 minutes.")
                    logger.warning(f"ACCOUNT_LOCKED | IP: {client_ip} | User: {user_obj.email} | Reason: Max failed login attempts")
                else:
                    remaining_attempts = 5 - profile.failed_login_attempts
                    context['remaining_attempts'] = remaining_attempts
                    messages.error(request, f"Incorrect Username or Password! {remaining_attempts} attempts remaining.")
            except User.DoesNotExist:
                messages.error(request, "Incorrect Username or Password!")
            except UserProfile.DoesNotExist:
                messages.error(request, "Incorrect Username or Password!")

    return render(request, 'login.html', context)

def logout_view(request):
    if request.user.is_authenticated:
        user_email = request.user.email
        auth_logout(request)
        logger.info(f"LOGOUT | User: {user_email}")
    return redirect('index')

@ensure_csrf_cookie
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
        # Ensure user has a profile (for OAuth users)
        UserProfile.objects.get_or_create(
            user=request.user,
            defaults={'contactnumber': '', 'role': 'customer'}
        )
        
        data = json.loads(request.body)
        name = data.get('name')
        quantity = int(data.get('quantity', 1))
        if quantity <= 0:
            return JsonResponse({'message': 'Quantity must be greater than zero'}, status=400)
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
    MAX_TOTAL_QUANTITY = 15
    ORDER_COOLDOWN_MINUTES = 5
    MAX_DAILY_ORDERS = 3
    
    # Total quantity validation
    total_quantity = sum(item.quantity for item in cart_items)
    if total_quantity > MAX_TOTAL_QUANTITY:
        AuditLog.objects.create(
            user=request.user,
            action='total_quantity_limit_failed',
            description=f"Checkout failed: Total quantity {total_quantity} exceeds maximum {MAX_TOTAL_QUANTITY}",
            ip_address=request.META.get('REMOTE_ADDR')
        )
        return JsonResponse({'success': False, 'message': f'Total quantity cannot exceed {MAX_TOTAL_QUANTITY} items'}, status=400)
    
    # Order cooldown validation (only for successfully paid orders)
    last_paid_order = Order.objects.filter(
        user=request.user,
        status__in=['processing', 'claimed']  # Successfully paid orders
    ).order_by('-ordered_at').first()
    if last_paid_order:
        time_since_last_order = timezone.now() - last_paid_order.ordered_at
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

    # Generate a stable order reference at checkout creation so it is available immediately.
    order_reference = generate_order_reference_number()
    request.session['order_reference'] = order_reference

    shipping_fee = Decimal('0.00')
    subtotal = Decimal('0.00')
    order_items = []

    for item in cart_items.select_related('product'):
        if item.quantity <= 0:
            logger.warning(f"CHECKOUT_INVALID_QUANTITY | user={request.user.id} | product={item.product.name} | quantity={item.quantity}")
            return JsonResponse({'success': False, 'message': f'Invalid quantity for {item.product.name}'}, status=400)

        product_price = item.product.price
        if product_price is None:
            logger.error(f"CHECKOUT_MISSING_PRICE | user={request.user.id} | product={item.product.name}")
            return JsonResponse({'success': False, 'message': f'Price not found for {item.product.name}'}, status=400)

        line_subtotal = product_price * item.quantity
        subtotal += line_subtotal
        order_items.append({
            'name': item.product.name,
            'price': str(product_price),
            'quantity': item.quantity,
            'subtotal': str(line_subtotal)
        })

        # Update stock
        item.product.stock -= item.quantity
        if item.product.stock <= 0:
            item.product.is_available = False
        item.product.save()

        Order.objects.create(
            user=request.user,
            session_id=session_id,
            item_name=item.product.name,
            item_price=item.product.price,
            quantity=item.quantity,
            reference_number=order_reference
        )

    total_price = subtotal + shipping_fee
    if total_price <= 0:
        logger.error(f"CHECKOUT_ZERO_TOTAL | user={request.user.id} | subtotal={subtotal} | shipping_fee={shipping_fee}")
        return JsonResponse({'success': False, 'message': 'Invalid order total. Please verify your cart.'}, status=400)

    logger.info(f"CHECKOUT_SUMMARY | user={request.user.id} | reference={order_reference} | items={order_items} | subtotal={subtotal} | shipping_fee={shipping_fee} | grand_total={total_price}")

    request.session['checkout_subtotal'] = str(subtotal)
    request.session['checkout_shipping_fee'] = str(shipping_fee)
    request.session['total_price'] = str(total_price)
    cart_items.delete()

    return JsonResponse({'success': True})

@login_required
def pickup_view(request):
    session_id = request.session.get('checkout_session_id')
    total_price = Decimal(request.session.get('total_price', '0.00'))
    shipping_fee = Decimal(request.session.get('checkout_shipping_fee', '0.00'))
    subtotal = Decimal(request.session.get('checkout_subtotal', '0.00'))

    if not session_id or not Order.objects.filter(session_id=session_id).exists():
        messages.error(request, "No active order to bill.")
        return redirect('menu')

    if total_price <= 0:
        logger.error(f"PICKUP_INVALID_TOTAL | user={request.user.id} | total_price={total_price} | session_id={session_id}")
        messages.error(request, "Unable to proceed with checkout because the order total is invalid.")
        return redirect('menu')

    # Group orders by item name and sum quantities
    orders = Order.objects.filter(session_id=session_id, user=request.user)
    grouped_orders = {}
    for order in orders:
        if order.item_name in grouped_orders:
            grouped_orders[order.item_name]['quantity'] += order.quantity
        else:
            grouped_orders[order.item_name] = {
                'item_name': order.item_name,
                'item_price': order.item_price,
                'quantity': order.quantity
            }
    
    # Convert grouped orders back to a list for template rendering
    orders_list = list(grouped_orders.values())
        
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
            
            # Update Order records with contact and payment information immediately
            # This ensures data is available in staff dashboard even before payment completion
            Order.objects.filter(session_id=session_id, user=request.user).update(
                contact_number=form.cleaned_data['contact_number'],
                payment_option=payment_option,
                total_amount=total_amount,
                amount_paid=amount_paid,
                remaining_balance=remaining_balance,
                pickup_availability_date=pickup_availability_date
            )
            
            # Create PayMongo checkout session using the current host / port
            success_url = request.build_absolute_uri(reverse('payment_success'))
            cancel_url = request.build_absolute_uri(reverse('menu'))
            checkout_info = request.session.get('checkout_info', {})
            checkout_info['session_id'] = session_id
            payment_result = create_paymongo_checkout(
                amount=amount_paid,
                description=f"Order Payment - {payment_option.title()} - {request.user.username}",
                user=request.user,
                success_url=success_url,
                cancel_url=cancel_url,
                checkout_info=checkout_info
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
                    'orders': orders_list
                })
        else:
            messages.error(request, "Invalid form data. Please verify all inputs.")
    else:
        form = PickupForm(user=request.user)
        
    return render(request, 'pickup.html', {
        'form': form,
        'total_price': total_price,
        'orders': orders_list
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
            
            # Get orders for this session
            orders = Order.objects.filter(session_id=session_id, user=request.user)
            
            # Get or generate reference number using order's purchase date
            first_order = orders.first()
            if first_order and first_order.reference_number and first_order.reference_number.startswith('DRMP-'):
                reference_number = first_order.reference_number
            else:
                # Generate reference using the order's purchase date
                reference_number = generate_order_reference_number(first_order.ordered_at if first_order else None)
            
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
            orders.update(
                payment_option=checkout_info['payment_option'],
                total_amount=checkout_info['total_amount'],
                amount_paid=checkout_info['amount_paid'],
                remaining_balance=checkout_info['remaining_balance'],
                pickup_availability_date=timezone.datetime.strptime(checkout_info['pickup_availability_date'], '%Y-%m-%d').date(),
                reference_number=reference_number,
                contact_number=checkout_info['contact_number'],
                status='confirmed'
            )
            
            # Deduct stock for all ordered items
            stock_deduction_result = deduct_stock_for_orders(session_id, payment.id, request.user)
            
            if not stock_deduction_result['success']:
                # Log stock deduction failure but don't fail the order
                AuditLog.objects.create(
                    user=request.user,
                    action='stock_validation_failed',
                    description=f"Stock deduction failed for order {reference_number}: {stock_deduction_result.get('error', 'Unknown error')}",
                    ip_address=request.META.get('REMOTE_ADDR')
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
    receipt = Receipt.objects.filter(user=request.user).order_by('-id').first()
    
    if not receipt:
        messages.error(request, "No order found.")
        return redirect('menu')
    
    orders = Order.objects.filter(session_id=receipt.session_id, user=request.user)
    order_details = []
    total_cost = Decimal('0.00')
    for order in orders:
        line_total = order.item_price * order.quantity
        order_details.append({
            'item_name': order.item_name,
            'quantity': order.quantity,
            'unit_price': order.item_price,
            'line_total': line_total
        })
        total_cost += line_total

    return render(request, 'order_success.html', {
        'receipt': receipt,
        'orders': orders,
        'order_details': order_details,
        'total_quantity': sum(item['quantity'] for item in order_details),
        'total_cost': total_cost,
    })

@login_required
def receipt_view(request):
    receipt_id = request.GET.get('receipt_id')
    session_id_param = request.GET.get('session_id')

    if receipt_id:
        receipt = get_object_or_404(Receipt, id=receipt_id, user=request.user)
    elif session_id_param:
        receipt = Receipt.objects.filter(session_id=session_id_param, user=request.user).order_by('-id').first()
        if not receipt:
            messages.error(request, "Receipt not found for this session.")
            return redirect('profile')
    else:
        session_id = request.session.get('checkout_session_id')
        if not session_id:
            return redirect('menu')
        receipt = get_object_or_404(Receipt, session_id=session_id, user=request.user)

    orders = Order.objects.filter(session_id=receipt.session_id, user=request.user)
    order_details = []
    total_quantity = 0
    total_cost = Decimal('0.00')
    for order in orders:
        line_total = order.item_price * order.quantity
        order_details.append({
            'item_name': order.item_name,
            'quantity': order.quantity,
            'unit_price': order.item_price,
            'line_total': line_total
        })
        total_quantity += order.quantity
        total_cost += line_total

    profile = getattr(request.user, 'profile', None)
    contact_number = profile.contactnumber if profile else 'Not Provided'

    reference_number = receipt.reference_number or orders.filter(reference_number__isnull=False).values_list('reference_number', flat=True).first() or receipt.session_id[:8]

    return render(request, 'receipt.html', {
        'receipt': receipt,
        'orders': orders,
        'order_details': order_details,
        'total_quantity': total_quantity,
        'total_cost': total_cost,
        'contact_number': contact_number,
        'reference_number': reference_number
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
                ip_address=get_client_ip(request)
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
        form = ProductForm(request.POST, request.FILES, instance=product)
        if form.is_valid():
            edited_product = form.save(commit=False)
            # If no new image uploaded, keep the existing image name in DB
            if 'image' not in request.FILES:
                edited_product.image = product.image
            edited_product.save()
            AuditLog.objects.create(
                user=request.user,
                action='product_edit',
                description=f"Edited product: {product.name}",
                product_id=product.id,
                ip_address=get_client_ip(request)
            )
            messages.success(request, "Product updated successfully!")
            return redirect('staff_products')
    else:
        form = ProductForm(instance=product)

    return render(request, 'staff/product_form.html', {
        'form': form,
        'title': 'Edit Product',
        'product': product
    })

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
            ip_address=get_client_ip(request)
        )
        messages.success(request, "Product deleted successfully!")
        return redirect('staff_products')
    
    return render(request, 'staff/product_confirm_delete.html', {'product': product})

@staff_required
def staff_orders(request):
    from datetime import timedelta
    
    # Get the active tab from query parameter (default: pending)
    active_tab = request.GET.get('tab', 'pending')
    
    # Filter orders based on active tab
    if active_tab == 'pending':
        orders = Order.objects.filter(status='pending').select_related('user').order_by('-ordered_at')
    elif active_tab == 'processing':
        orders = Order.objects.filter(status='processing').select_related('user').order_by('-ordered_at')
    elif active_tab == 'claimed':
        orders = Order.objects.filter(status='claimed').select_related('user').order_by('-ordered_at')
    else:
        orders = Order.objects.all().select_related('user').order_by('-ordered_at')
    
    # Get receipt data for each order
    for order in orders:
        # Try to get receipt for this order's session
        receipt = Receipt.objects.filter(session_id=order.session_id).first()
        
        if receipt:
            order.customer_name = receipt.full_name or order.user.get_full_name()
            order.customer_email = receipt.user.email
            order.customer_contact = order.contact_number if order.contact_number else receipt.contact_number if receipt.contact_number else (order.user.userprofile.contactnumber if hasattr(order.user, 'userprofile') else 'N/A')
            order.payment_option_display = order.payment_option if order.payment_option else receipt.payment_option if receipt.payment_option else 'N/A'
        else:
            # Fallback to order data if no receipt exists
            order.customer_name = order.user.get_full_name()
            order.customer_email = order.user.email
            order.customer_contact = order.contact_number if order.contact_number else (order.user.userprofile.contactnumber if hasattr(order.user, 'userprofile') else 'N/A')
            order.payment_option_display = order.payment_option if order.payment_option else 'N/A'
        
        # Get updated by staff email
        order.updated_by_email = order.updated_by.email if order.updated_by else 'N/A'
        
        # Calculate pickup date (3 days after order date)
        if order.pickup_availability_date:
            order.pickup_date_display = order.pickup_availability_date
        elif order.ordered_at:
            order.pickup_date_display = order.ordered_at + timedelta(days=3)
        else:
            order.pickup_date_display = None
        
        # Ensure quantity is set (default to 1 for old orders)
        if not hasattr(order, 'quantity') or order.quantity is None:
            order.quantity = 1
    
    paginator = Paginator(orders, 10)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    return render(request, 'staff/orders.html', {
        'page_obj': page_obj,
        'active_tab': active_tab
    })

@staff_required
def move_to_processing(request, order_id):
    """Move order from Pending to Processing"""
    if request.method != 'POST':
        return JsonResponse({'success': False, 'error': 'Invalid request method'})
    
    try:
        order = get_object_or_404(Order, id=order_id)
        
        # Validate status transition
        if order.status != 'pending':
            return JsonResponse({'success': False, 'error': 'Order must be in Pending status to move to Processing'})
        
        old_status = order.status
        order.status = 'processing'
        order.processed_at = timezone.now()
        order.updated_by = request.user
        order.save()
        
        # Log audit
        AuditLog.objects.create(
            user=request.user,
            action='order_status_update',
            description=f"Moved order {order.id} from {old_status} to Processing",
            order_id=order.id,
            ip_address=request.META.get('REMOTE_ADDR')
        )
        
        return JsonResponse({'success': True, 'message': 'Order moved to Processing successfully'})
        
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)})

@staff_required
def move_to_claimed(request, order_id):
    """Move order from Processing to Claimed"""
    if request.method != 'POST':
        return JsonResponse({'success': False, 'error': 'Invalid request method'})
    
    try:
        order = get_object_or_404(Order, id=order_id)
        
        # Validate status transition
        if order.status != 'processing':
            return JsonResponse({'success': False, 'error': 'Order must be in Processing status to move to Claimed'})
        
        old_status = order.status
        order.status = 'claimed'
        order.claimed_at = timezone.now()
        order.updated_by = request.user
        order.save()
        
        # Log audit
        AuditLog.objects.create(
            user=request.user,
            action='order_status_update',
            description=f"Moved order {order.id} from {old_status} to Claimed",
            order_id=order.id,
            ip_address=request.META.get('REMOTE_ADDR')
        )
        
        return JsonResponse({'success': True, 'message': 'Order moved to Claimed successfully'})
        
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)})

@staff_required
@csrf_exempt
def update_order_status(request, order_id):
    """Update order status via AJAX"""
    if request.method != 'POST':
        return JsonResponse({'success': False, 'error': 'Invalid request method'})
    
    try:
        data = json.loads(request.body)
        new_status = data.get('status')
        
        if not new_status:
            return JsonResponse({'success': False, 'error': 'Status is required'})
        
        order = get_object_or_404(Order, id=order_id)
        old_status = order.status
        order.status = new_status
        order.updated_by = request.user
        order.save()
        
        # Log audit
        AuditLog.objects.create(
            user=request.user,
            action='order_status_update',
            description=f"Updated order {order.id} status from {old_status} to {new_status}",
            order_id=order.id,
            ip_address=request.META.get('REMOTE_ADDR')
        )
        
        return JsonResponse({'success': True, 'message': 'Order status updated successfully'})
        
    except json.JSONDecodeError:
        return JsonResponse({'success': False, 'error': 'Invalid JSON data'})
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)})

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
                ip_address=get_client_ip(request)
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
                ip_address=get_client_ip(request)
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
                    ip_address=get_client_ip(request)
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
            ip_address=get_client_ip(request)
        )
        messages.success(request, "Staff account deleted successfully!")
        return redirect('admin_staff_list')
    
    return render(request, 'admin/staff_confirm_delete.html', {'user': user})

@login_required
def change_password_view(request):
    if request.method == 'POST':
        form = PasswordChangeForm(request.user, request.POST)
        if form.is_valid():
            user = form.save()
            update_session_auth_hash(request, user)  # Important to keep user logged in
            messages.success(request, "Your password was successfully updated.")
            logger.info(f"PASSWORD_CHANGE_SUCCESS | User: {request.user.email}")
            return redirect('profile')
        else:
            messages.error(request, "Please correct the error below.")
            logger.warning(f"PASSWORD_CHANGE_FAILED | User: {request.user.email} | Reason: Form errors: {form.errors.as_text()}")
    else:
        form = PasswordChangeForm(request.user)
    return render(request, 'change_password.html', {'form': form})

@login_required
def change_email_view(request):
    if request.method == 'POST':
        form = EmailChangeForm(request.user, request.POST)
        if form.is_valid():
            new_email = form.cleaned_data.get('new_email')
            user = request.user
            old_email = user.email
            user.email = new_email
            user.save()
            messages.success(request, "Your email was successfully updated.")
            logger.info(f"EMAIL_CHANGE_SUCCESS | User: {old_email} | New Email: {new_email}")
            return redirect('profile')
        else:
            messages.error(request, "Please correct the error below.")
            logger.warning(f"EMAIL_CHANGE_FAILED | User: {request.user.email} | Reason: Form errors: {form.errors.as_text()}")
    else:
        form = EmailChangeForm(request.user)
    return render(request, 'change_email.html', {'form': form})

@login_required
def profile_view(request):
    # Create profile if it doesn't exist (for OAuth users)
    profile, created = UserProfile.objects.get_or_create(
        user=request.user,
        defaults={'contactnumber': '', 'role': 'customer'}
    )
    return render(request, 'profile.html', {
        'profile': profile
    })

@login_required
def purchase_history_view(request):
    """
    Display purchase history grouped by order reference.
    One row per order, with aggregated product information.
    """
    # Get unique orders for this user, grouped by reference_number or session_id
    orders_qs = Order.objects.filter(
        user=request.user
    ).select_related('user').order_by('-ordered_at')
    
    if not orders_qs.exists():
        from django.core.paginator import Paginator
        return render(request, 'purchase_history.html', {
            'page_obj': Paginator([], 10).get_page(1)
        })
    
    # Group orders by session_id (one order session per purchase)
    seen_sessions = set()
    history_entries = []
    
    for order in orders_qs:
        session_id = order.session_id
        if session_id in seen_sessions:
            continue  # Skip, already processed this session
        
        seen_sessions.add(session_id)
        
        # Get all items in this order session
        session_orders = Order.objects.filter(
            session_id=session_id,
            user=request.user
        ).select_related('user')
        
        # Build product list with quantities
        product_items = {}
        total_quantity = 0
        total_cost = Decimal('0.00')
        
        for item in session_orders:
            key = item.item_name
            if key not in product_items:
                product_items[key] = {
                    'name': item.item_name,
                    'quantity': 0,
                    'price': item.item_price
                }
            product_items[key]['quantity'] += item.quantity
            total_quantity += item.quantity
            total_cost += item.item_price * item.quantity
        
        # Format product display
        product_display = []
        for item_name, item_data in product_items.items():
            if item_data['quantity'] > 1:
                product_display.append(f"{item_name} x{item_data['quantity']}")
            else:
                product_display.append(item_name)
        
        products_str = ', '.join(product_display[:3])
        if len(product_display) > 3:
            products_str += '...'
        
        # Get order reference (should be consistent across session)
        reference_number = order.reference_number or session_id[:8]
        
        # Get receipt for this order if it exists
        receipt = Receipt.objects.filter(
            session_id=session_id,
            user=request.user
        ).first()
        
        # Determine payment status and amount
        if receipt and receipt.amount_paid:
            payment_status = 'paid' if receipt.amount_paid >= total_cost else 'partial'
            total_paid = receipt.amount_paid
        else:
            payment_status = order.status
            total_paid = order.amount_paid or Decimal('0.00')
        
        # Get the latest status from all orders in this session
        latest_order = session_orders.order_by('-ordered_at').first()
        status_display = latest_order.get_status_display() if latest_order else 'Pending'
        
        history_entries.append({
            'reference_number': reference_number,
            'session_id': session_id,
            'products': products_str or 'No items',
            'items': total_quantity,
            'total_paid': total_paid if total_paid else total_cost,
            'ordered_date': order.ordered_at,
            'status': payment_status,
            'status_display': status_display,
            'receipt_id': receipt.id if receipt else None,
            'has_payment': bool(receipt and receipt.amount_paid),
        })
    
    from django.core.paginator import Paginator
    paginator = Paginator(history_entries, 10)
    page_number = request.GET.get('page', 1)
    page_obj = paginator.get_page(page_number)
    
    return render(request, 'purchase_history.html', {
        'page_obj': page_obj
    })

@login_required
@require_POST
def toggle_mfa(request):
    """
    Toggle email MFA for the authenticated user.
    
    Expected POST data: {'type': 'email'}
    
    Returns JSON with success status and updated MFA state.
    """
    try:
        # Parse JSON request body
        data = json.loads(request.body)
        mfa_type = data.get('type', '').lower()
        
        # Validate MFA type
        if mfa_type != 'email':
            return JsonResponse({
                'success': False,
                'message': f'Invalid MFA type: {mfa_type}. Only "email" is supported.'
            }, status=400)
        
        # Get user profile
        try:
            profile = request.user.profile
        except UserProfile.DoesNotExist:
            return JsonResponse({
                'success': False,
                'message': 'User profile not found. Please contact support.'
            }, status=404)
        
        # Toggle email-only MFA setting
        profile.mfa_email_enabled = not profile.mfa_email_enabled
        profile.save()
        logger.info(f"MFA_TOGGLED | User: {request.user.email} | Enabled: {profile.mfa_email_enabled}")
        
        return JsonResponse({
            'success': True,
            'type': 'email',
            'message': f'Email MFA has been {"enabled" if profile.mfa_email_enabled else "disabled"}',
            'mfa_email_enabled': profile.mfa_email_enabled
        })
    
    except json.JSONDecodeError:
        return JsonResponse({
            'success': False,
            'message': 'Invalid JSON in request body'
        }, status=400)
    
    except Exception as e:
        return JsonResponse({
            'success': False,
            'message': f'Server error: {str(e)}'
        }, status=500)

def verify_mfa(request):
    """2FA verification page"""
    mfa_user_id = request.session.get('mfa_user_id')
    mfa_method = request.session.get('mfa_method')
    
    if not mfa_user_id or not mfa_method:
        messages.error(request, "Invalid 2FA session. Please login again.")
        logger.warning("MFA_VERIFY_FAILED | Reason: No MFA session variables found")
        return redirect('login')
    
    user = get_object_or_404(User, id=mfa_user_id)
    
    if request.method == 'POST':
        code = request.POST.get('code', '').strip()
        client_ip = get_client_ip(request)
        
        # Rate limiting: Max 5 attempts
        mfa_failed_attempts_key = f'mfa_failed_attempts_{mfa_user_id}'
        failed_attempts = cache.get(mfa_failed_attempts_key, 0)
        
        if failed_attempts >= 5:
            MFACode.objects.filter(user=user).delete()
            if 'mfa_user_id' in request.session:
                del request.session['mfa_user_id']
            if 'mfa_method' in request.session:
                del request.session['mfa_method']
            messages.error(request, "Too many failed 2FA attempts. Please login again.")
            logger.warning(f"MFA_LOCKOUT | IP: {client_ip} | User: {user.email} | Reason: Max failed 2FA attempts exceeded")
            return redirect('login')
        
        try:
            mfa_code = MFACode.objects.get(user=user)
            
            # Check if code is expired
            if mfa_code.is_expired():
                messages.error(request, "Verification code has expired. Please login again.")
                logger.warning(f"MFA_VERIFY_FAILED | IP: {client_ip} | User: {user.email} | Reason: Code expired")
                del request.session['mfa_user_id']
                del request.session['mfa_method']
                return redirect('login')
            
            # Check if code matches
            if mfa_code.code == code:
                # Code is correct, log in the user
                auth_login(request, user, backend='django.contrib.auth.backends.ModelBackend')
                logger.info(f"MFA_VERIFY_SUCCESS | IP: {client_ip} | User: {user.email}")
                
                # Clean up MFA code and cached attempts
                mfa_code.delete()
                cache.delete(mfa_failed_attempts_key)
                del request.session['mfa_user_id']
                del request.session['mfa_method']
                
                messages.success(request, "Login successful!")
                return redirect('index')
            else:
                # Increment failed attempts
                failed_attempts += 1
                cache.set(mfa_failed_attempts_key, failed_attempts, 600)  # expires in 10 mins
                
                if failed_attempts >= 5:
                    mfa_code.delete()
                    if 'mfa_user_id' in request.session:
                        del request.session['mfa_user_id']
                    if 'mfa_method' in request.session:
                        del request.session['mfa_method']
                    messages.error(request, "Too many failed 2FA attempts. Please login again.")
                    logger.warning(f"MFA_LOCKOUT | IP: {client_ip} | User: {user.email} | Reason: Max failed 2FA attempts")
                    return redirect('login')
                
                remaining_attempts = 5 - failed_attempts
                messages.error(request, f"Invalid verification code. {remaining_attempts} attempts remaining.")
                logger.warning(f"MFA_VERIFY_FAILED | IP: {client_ip} | User: {user.email} | Reason: Incorrect code submitted")
        
        except MFACode.DoesNotExist:
            messages.error(request, "No verification code found. Please login again.")
            logger.warning(f"MFA_VERIFY_FAILED | IP: {client_ip} | User: {user.email} | Reason: No code in database")
            del request.session['mfa_user_id']
            del request.session['mfa_method']
            return redirect('login')
    
    return render(request, 'verify_mfa.html', {
        'mfa_method': mfa_method,
        'user_email': user.email
    })

# ============================================================================
# Admin TOTP Views
# ============================================================================

@admin_required
def admin_totp_setup(request):
    """Setup TOTP for admin user"""
    import pyotp
    import qrcode
    import io
    import base64

    try:
        totp_secret = request.user.totp_secret
    except:
        totp_secret = None

    if totp_secret and totp_secret.is_verified:
        messages.info(request, "TOTP is already enabled for your account.")
        return redirect('admin:index')

    if request.method == 'POST':
        code = request.POST.get('code', '').strip()

        if not code:
            messages.error(request, "Please enter a verification code.")
            return redirect('admin_totp_setup')

        # Generate new secret if not exists
        if not totp_secret:
            secret = pyotp.random_base32()
            from bakery.models import TOTPSecret
            totp_secret = TOTPSecret.objects.create(user=request.user, secret=secret)

        # Verify the code
        totp = pyotp.TOTP(totp_secret.secret)
        if totp.verify(code):
            totp_secret.is_verified = True
            totp_secret.save()
            messages.success(request, "TOTP has been successfully enabled for your account.")
            logger.info(f"ADMIN_TOTP_ENABLED | User: {request.user.email}")
            return redirect('admin:index')
        else:
            messages.error(request, "Invalid verification code. Please try again.")
            return redirect('admin:admin_totp_setup')

    # Generate new secret and QR code
    if not totp_secret:
        secret = pyotp.random_base32()
        from bakery.models import TOTPSecret
        totp_secret = TOTPSecret.objects.create(user=request.user, secret=secret)

    totp = pyotp.TOTP(totp_secret.secret)
    qr_uri = totp.provisioning_uri(
        name=request.user.email,
        issuer_name='Dough Re Mi Patisserie Admin'
    )

    # Generate QR code
    qr = qrcode.QRCode()
    qr.add_data(qr_uri)
    qr.make()
    img = qr.make_image()

    buffer = io.BytesIO()
    img.save(buffer, format='PNG')
    qr_code_base64 = base64.b64encode(buffer.getvalue()).decode()

    return render(request, 'admin/totp_setup.html', {
        'qr_code': qr_code_base64,
        'secret': totp_secret.secret,
        'user_email': request.user.email
    })

@admin_required
def admin_totp_disable(request):
    """Disable TOTP for admin user"""
    if request.method == 'POST':
        try:
            totp_secret = request.user.totp_secret
            totp_secret.delete()
            messages.success(request, "TOTP has been disabled for your account.")
            logger.info(f"ADMIN_TOTP_DISABLED | User: {request.user.email}")
        except:
            pass
        return redirect('admin:index')

    return render(request, 'admin/totp_disable_confirm.html')

def verify_admin_totp(request):
    """Verify TOTP for admin login"""
    import pyotp

    totp_user_id = request.session.get('totp_user_id')

    if not totp_user_id:
        messages.error(request, "Invalid TOTP session. Please login again.")
        return redirect('admin:login')

    user = get_object_or_404(User, id=totp_user_id)

    if request.method == 'POST':
        code = request.POST.get('code', '').strip()
        client_ip = get_client_ip(request)

        # Rate limiting
        totp_attempts_key = f'totp_attempts_{totp_user_id}'
        attempts = cache.get(totp_attempts_key, 0)

        if attempts >= 5:
            del request.session['totp_user_id']
            messages.error(request, "Too many failed TOTP attempts. Please login again.")
            logger.warning(f"ADMIN_TOTP_LOCKOUT | IP: {client_ip} | User: {user.email}")
            return redirect('admin:login')

        try:
            totp_secret = user.totp_secret
            if not totp_secret.is_verified:
                messages.error(request, "TOTP is not enabled for this account.")
                return redirect('admin:login')

            totp = pyotp.TOTP(totp_secret.secret)
            if totp.verify(code):
                auth_login(request, user, backend='django.contrib.auth.backends.ModelBackend')
                request.session['admin_totp_verified'] = True
                del request.session['totp_user_id']
                cache.delete(totp_attempts_key)
                logger.info(f"ADMIN_TOTP_VERIFY_SUCCESS | IP: {client_ip} | User: {user.email}")
                return redirect('admin:index')
            else:
                attempts += 1
                cache.set(totp_attempts_key, attempts, 600)
                remaining = 5 - attempts
                messages.error(request, f"Invalid TOTP code. {remaining} attempts remaining.")
                logger.warning(f"ADMIN_TOTP_VERIFY_FAILED | IP: {client_ip} | User: {user.email}")
        except:
            messages.error(request, "TOTP is not enabled for this account.")
            return redirect('admin:login')

    return render(request, 'admin/verify_totp.html', {'user_email': user.email})
