import json
import logging
import random
import string
from decimal import Decimal

logger = logging.getLogger('security')
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import authenticate, login as auth_login, logout as auth_logout, update_session_auth_hash
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse, HttpResponse
from django.views.decorators.http import require_POST
from django.views.decorators.csrf import ensure_csrf_cookie
from django.contrib import messages
from django.contrib.auth.models import User
from django.contrib.auth.forms import SetPasswordForm, PasswordChangeForm
from django.core.paginator import Paginator
from django.core.mail import send_mail
from django.utils import timezone
from datetime import timedelta
from django.core.cache import cache
from django.core.exceptions import ObjectDoesNotExist

from bakery.models import Product, CartItem, Order, Receipt, UserProfile, AuditLog, MFACode
from bakery.forms import SignUpForm, DeliveryForm, StaffCreateForm, StaffEditForm, ProductForm, OrderStatusForm, EmailChangeForm
from bakery.decorators import staff_required, admin_required
from bakery.signals import get_client_ip
from bakery.utils import generate_captcha_svg

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

This code will expire in 10 minutes.

If you did not request this code, please ignore this email.

Best regards,
Dough Re Mi Patisserie Team
        """
        send_mail(
            subject,
            message,
            'noreply@doughremipatisserie.com',
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
    expires_at = timezone.now() + timedelta(minutes=10)
    
    mfa_obj = MFACode.objects.create(
        user=user,
        code=code,
        method='email',
        expires_at=expires_at
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
            return render(request, 'signup.html', {'form': SignUpForm(request.POST)})

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
            
            UserProfile.objects.create(
                user=user,
                contactnumber=form.cleaned_data['contactnumber'],
                role='customer'  # Set default role to customer
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
        # Redirect based on role
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
            return render(request, 'login.html', context)

        email = request.POST.get('email')
        password = request.POST.get('password')

        # Rate limiting: Check IP-based rate limit (max 10 attempts per 15 minutes)
        rate_limit_key = f'login_rate_limit_{client_ip}'
        attempts = cache.get(rate_limit_key, 0)

        if attempts >= 10:
            messages.error(request, "Too many login attempts. Please try again later.")
            logger.warning(f"LOGIN_RATE_LIMIT | IP: {client_ip} | Attempts: {attempts}")
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
                    logger.warning(f"LOGIN_LOCKED | IP: {client_ip} | User: {user.email}")
                    return render(request, 'login.html', context)

                # Reset failed attempts on successful authentication
                profile.reset_failed_attempts()
                
                # Check if user has email 2FA enabled
                if profile.mfa_email_enabled:
                    create_mfa_code(user)
                    request.session['mfa_user_id'] = user.id
                    request.session['mfa_method'] = 'email'
                    messages.info(request, "Verification code sent to your email.")
                    logger.info(f"LOGIN_MFA_CHALLENGE | IP: {client_ip} | User: {user.email}")
                    return redirect('verify_mfa')
            except UserProfile.DoesNotExist:
                # Create profile if it doesn't exist
                UserProfile.objects.create(user=user, contactnumber='')
            
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
        if quantity <= 0:
            return JsonResponse({'message': 'Quantity must be greater than zero'}, status=400)
        product = get_object_or_404(Product, name=name)
        
        cart_item, created = CartItem.objects.get_or_create(user=request.user, product=product)
        if created:
            cart_item.quantity = quantity
        else:
            cart_item.quantity += quantity
        cart_item.save()
            
        return JsonResponse({'message': 'Item added to cart'})
    except Exception as e:
        return JsonResponse({'message': f'Error adding item to cart: {str(e)}'}, status=400)

@login_required
@require_POST
def cart_remove(request):
    try:
        data = json.loads(request.body)
        index = data.get('index')
        
        cart_items = list(CartItem.objects.filter(user=request.user).order_by('id'))
        
        if 0 <= index < len(cart_items):
            item_to_remove = cart_items[index]
            if item_to_remove.quantity > 1:
                item_to_remove.quantity -= 1
                item_to_remove.save()
            else:
                item_to_remove.delete()
            return JsonResponse({'message': 'Item removed from cart'})
        else:
            return JsonResponse({'message': 'Item not found in cart'}, status=404)
    except Exception as e:
        return JsonResponse({'message': f'Error removing item from cart: {str(e)}'}, status=400)

@login_required
@require_POST
def checkout_view(request):
    cart_items = CartItem.objects.filter(user=request.user)
    if not cart_items.exists():
        return JsonResponse({'success': False, 'message': 'You need to add an item first!'})
        
    session_id = request.session.session_key
    if not session_id:
        request.session.create()
        session_id = request.session.session_key
        
    request.session['checkout_session_id'] = session_id
    
    total_price = Decimal('0.00')
    for item in cart_items:
        subtotal = item.product.price * item.quantity
        total_price += subtotal
        
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
def delivery_view(request):
    session_id = request.session.get('checkout_session_id')
    total_price = request.session.get('total_price', '0.00')
    
    if not session_id or not Order.objects.filter(session_id=session_id).exists():
        messages.error(request, "No active order to bill.")
        return redirect('menu')
        
    if request.method == 'POST':
        form = DeliveryForm(request.POST)
        if form.is_valid():
            Receipt.objects.create(
                user=request.user,
                session_id=session_id,
                total_price=float(total_price),
                housenumber=str(form.cleaned_data['houseNumber']),
                streetname=form.cleaned_data['street'],
                barangay=form.cleaned_data['barangay'],
                postalcode=str(form.cleaned_data['postalCode']),
                city=form.cleaned_data['city']
            )
            return redirect('receipt')
        else:
            messages.error(request, "Invalid form data. Please verify all inputs.")
    else:
        form = DeliveryForm()
        
    return render(request, 'delivery.html', {
        'form': form,
        'total_price': total_price
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
                ip_address=get_client_ip(request)
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
            ip_address=get_client_ip(request)
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

def profile_view(request):
    profile = request.user.profile
    return render(request, 'profile.html', {
        'profile': profile
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
                auth_login(request, user)
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
