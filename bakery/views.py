import json
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import authenticate, login as auth_login, logout as auth_logout
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.views.decorators.http import require_POST
from django.contrib import messages
from django.contrib.auth.models import User

from bakery.models import Product, CartItem, Order, Receipt, UserProfile
from bakery.forms import SignUpForm, DeliveryForm

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
                contactnumber=form.cleaned_data['contactnumber']
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
        return redirect('index')
    
    if request.method == 'POST':
        email = request.POST.get('email')
        password = request.POST.get('password')
        
        user = authenticate(request, username=email, password=password)
        if user is not None:
            auth_login(request, user)
            messages.success(request, "Login successful!")
            return redirect('index')
        else:
            messages.error(request, "Incorrect Username or Password!")
            
    return render(request, 'login.html')

def logout_view(request):
    if request.user.is_authenticated:
        auth_logout(request)
    return redirect('index')

def menu_view(request):
    products = Product.objects.all()
    return render(request, 'menu.html', {'products': products})

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
        product = get_object_or_404(Product, name=name)
        
        cart_item, created = CartItem.objects.get_or_create(user=request.user, product=product)
        if not created:
            cart_item.quantity += 1
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
    
    total_price = 0.00
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
