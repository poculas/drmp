var cart = [];

// ── Grab the CSRF token ───────────────────────────────────────────────────────
// Primary: window.CSRF_TOKEN injected by the Django template
// Fallback: read Django's csrftoken cookie (Django docs recommended approach)
function getCsrfToken() {
    if (window.CSRF_TOKEN) return window.CSRF_TOKEN;
    var name = 'csrftoken';
    var cookies = document.cookie.split(';');
    for (var i = 0; i < cookies.length; i++) {
        var c = cookies[i].trim();
        if (c.indexOf(name + '=') === 0) {
            return decodeURIComponent(c.substring(name.length + 1));
        }
    }
    return '';
}

// ── Show a brief toast notification ───────────────────────────────────────────
function showToast(message, success) {
    var existing = document.getElementById('cart-toast');
    if (existing) existing.remove();

    var toast = document.createElement('div');
    toast.id = 'cart-toast';
    toast.textContent = message;
    toast.style.cssText = [
        'position:fixed', 'bottom:24px', 'right:24px',
        'background:' + (success ? '#2e7d32' : '#c62828'),
        'color:#fff', 'padding:12px 20px', 'border-radius:8px',
        'font-size:14px', 'z-index:9999', 'box-shadow:0 4px 12px rgba(0,0,0,.25)',
        'transition:opacity .4s ease', 'opacity:1'
    ].join(';');
    document.body.appendChild(toast);

    setTimeout(function () { toast.style.opacity = '0'; }, 2500);
    setTimeout(function () { toast.remove(); }, 3000);
}

// ── Add item to cart ──────────────────────────────────────────────────────────
function addToCart(name, price, quantity, event) {
    if (event) event.stopPropagation();   // prevent card onclick from firing

    if (!window.USER_AUTHENTICATED) {
        window.location.href = '/login.php?next=/menu.php';
        return;
    }

    var qty = parseInt(quantity) || 1;
    var item = { name: name, price: price, quantity: qty };

    fetch('add-to-cart.php', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
            'X-CSRFToken': getCsrfToken()
        },
        body: JSON.stringify(item)
    })
    .then(function (response) {
        if (!response.ok) {
            return response.json().then(function (d) {
                throw new Error(d.message || 'Server error ' + response.status);
            });
        }
        return response.json();
    })
    .then(function (data) {
        showToast('✓ ' + name + ' added to cart!', true);
        loadCart();
    })
    .catch(function (error) {
        console.error('Error adding item to cart:', error);
        showToast('Failed to add item: ' + error.message, false);
    });
}

// ── Remove / decrement item from cart ─────────────────────────────────────────
function removeFromCart(index) {
    fetch('remove-from-cart.php', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
            'X-CSRFToken': getCsrfToken()
        },
        body: JSON.stringify({ index: index })
    })
    .then(function (response) { return response.json(); })
    .then(function (data) {
        loadCart();
    })
    .catch(function (error) {
        console.error('Error removing item from cart:', error);
        showToast('Failed to remove item.', false);
    });
}

// ── Load cart from server ─────────────────────────────────────────────────────
function loadCart() {
    fetch('get-cart.php')
        .then(function (response) { return response.json(); })
        .then(function (data) {
            cart = data.items || [];
            updateCart();
        })
        .catch(function (error) {
            console.error('Error loading cart:', error);
        });
}

// ── Render cart table ─────────────────────────────────────────────────────────
function updateCart() {
    var cartItemsElement = document.getElementById('cartItems');
    var cartTotalElement = document.getElementById('cartTotal');
    if (!cartItemsElement || !cartTotalElement) return;

    var total = 0;
    cartItemsElement.innerHTML = '';

    cart.forEach(function (item, index) {
        var subtotal = (item.subtotal != null) ? item.subtotal : (item.item_price * item.quantity);
        var row = document.createElement('tr');
        row.innerHTML =
            '<td>' + item.item_name + '</td>' +
            '<td>₱ ' + parseFloat(item.item_price).toFixed(2) + '</td>' +
            '<td>' + item.quantity + '</td>' +
            '<td><button onclick="removeFromCart(' + index + ')" class="btn btn-sm btn-danger" style="padding:1px 6px;">X</button></td>';
        cartItemsElement.appendChild(row);
        total += subtotal;
    });

    cartTotalElement.textContent = '₱ ' + total.toFixed(2);
}

// ── Wire up UI once DOM is ready ──────────────────────────────────────────────
document.addEventListener('DOMContentLoaded', function () {

    // Only initialise cart for logged-in users
    if (!window.USER_AUTHENTICATED) return;

    // Load cart items on page load
    loadCart();

    // Open cart sidebar
    var openCartBtn = document.getElementById('openCart');
    var cartEl = document.querySelector('.cart');
    if (openCartBtn && cartEl) {
        openCartBtn.addEventListener('click', function (e) {
            e.preventDefault();
            cartEl.classList.add('open');
        });
    }

    // Close cart sidebar
    var closeCartBtn = document.getElementById('closeCart');
    if (closeCartBtn && cartEl) {
        closeCartBtn.addEventListener('click', function () {
            cartEl.classList.remove('open');
        });
    }

    // Checkout button — server decides if cart has items
    var checkoutBtn = document.getElementById('checkOut');
    if (checkoutBtn) {
        checkoutBtn.addEventListener('click', function () {
            var btn = this;
            btn.disabled = true;
            btn.textContent = 'Processing...';

            fetch('checkout.php', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'X-CSRFToken': getCsrfToken()
                }
            })
            .then(function (response) {
                if (!response.ok) {
                    throw new Error('Server error ' + response.status);
                }
                return response.json();
            })
            .then(function (data) {
                if (data.success) {
                    window.location.href = 'delivery.php';
                } else {
                    alert(data.message || 'Checkout failed. Please try again.');
                    btn.disabled = false;
                    btn.textContent = 'Checkout';
                }
            })
            .catch(function (err) {
                console.error('Checkout error:', err);
                alert('Checkout failed: ' + err.message + '. Please try again.');
                btn.disabled = false;
                btn.textContent = 'Checkout';
            });
        });
    }
});