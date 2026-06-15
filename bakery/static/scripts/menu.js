var cart = [];

// ── Grab the CSRF token ───────────────────────────────────────────────────────
// Primary: window.CSRF_TOKEN injected by the Django template
// Fallback: read Django's csrftoken cookie (Django docs recommended approach)
function getCsrfToken() {
    if (window.CSRF_TOKEN) {
        console.log('Using CSRF_TOKEN from window:', window.CSRF_TOKEN);
        return window.CSRF_TOKEN;
    }
    var name = 'csrftoken';
    var cookies = document.cookie.split(';');
    for (var i = 0; i < cookies.length; i++) {
        var c = cookies[i].trim();
        if (c.indexOf(name + '=') === 0) {
            var token = decodeURIComponent(c.substring(name.length + 1));
            console.log('Using CSRF_TOKEN from cookie:', token);
            return token;
        }
    }
    console.log('No CSRF token found');
    return '';
}

// Function to show notification popup (floating at top-right)
function showNotification(message, type = 'success') {
    // Remove existing notification if any
    const existingNotification = document.querySelector('.notification-popup');
    if (existingNotification) {
        existingNotification.remove();
    }

    // Create notification element
    const notification = document.createElement('div');
    notification.className = 'notification-popup';
    notification.textContent = message;
    notification.setAttribute('data-position', 'top-right');

    // Set color based on type
    if (type === 'success') {
        notification.style.backgroundColor = '#28a745';
    } else if (type === 'error') {
        notification.style.backgroundColor = '#dc3545';
    } else if (type === 'warning') {
        notification.style.backgroundColor = '#ffc107';
    } else if (type === 'info') {
        notification.style.backgroundColor = '#17a2b8';
    }

    // Add to body
    document.body.appendChild(notification);

    // Remove after 6 seconds
    setTimeout(() => {
        notification.remove();
    }, 6000);
}

// ── Add item to cart ──────────────────────────────────────────────────────────
function addToCart(name, price, quantity, event) {
    if (event) event.stopPropagation();   // prevent card onclick from firing

    if (!window.isUserLoggedIn) {
        window.location.href = 'login.php';
        return;
    }
    
    const item = { name: name, price: price, quantity: quantity };

    fetch('add-to-cart.php', {
        method: 'POST',
        headers: { 
            'Content-Type': 'application/json',
            'X-CSRFToken': getCsrfToken()
        },
        body: JSON.stringify(item)
    })
    .then(response => {
        if (!response.ok) {
            // Check if redirected to login (HTML response instead of JSON)
            if (response.headers.get('content-type') && response.headers.get('content-type').includes('text/html')) {
                window.location.href = 'login.php';
                return;
            }
            throw new Error('Network response was not ok');
        }
        return response.json();
    })
    .then(data => {
        if (data) {
            showNotification(data.message || '✓ ' + name + ' added to cart!', 'success');
            loadCart();
        }
    })
    .catch(error => {
        console.error('Error adding item to cart:', error);
        showNotification('Error adding item to cart', 'error');
    });
}

// Function to get CSRF token from cookies
function getCookie(name) {
    let cookieValue = null;
    if (document.cookie && document.cookie !== '') {
        const cookies = document.cookie.split(';');
        for (let i = 0; i < cookies.length; i++) {
            const cookie = cookies[i].trim();
            if (cookie.substring(0, name.length + 1) === (name + '=')) {
                cookieValue = decodeURIComponent(cookie.substring(name.length + 1));
                break;
            }
        }
    }
    return cookieValue;
}

// ── Remove / decrement item from cart ─────────────────────────────────────────
function removeFromCart(index) {
    fetch('remove-from-cart.php', {
        method: 'POST',
        headers: { 
            'Content-Type': 'application/json',
            'X-CSRFToken': getCsrfToken()
        },
        body: JSON.stringify({ index: index, action: 'remove' })
    })
    .then(response => response.json())
    .then(data => {
        showNotification(data.message, 'success');
        loadCart();
    })
    .catch(error => {
        console.error('Error removing item from cart:', error);
        showNotification('Error removing item from cart', 'error');
    });
}

// Function to increment cart item quantity
function incrementCartItem(index) {
    fetch('update-cart-quantity.php', {
        method: 'POST',
        headers: { 
            'Content-Type': 'application/json',
            'X-CSRFToken': getCsrfToken()
        },
        body: JSON.stringify({ index: index, action: 'increment' })
    })
    .then(response => response.json())
    .then(data => {
        if (data.success) {
            loadCart();
        } else {
            showNotification(data.message, 'error');
        }
    })
    .catch(error => {
        console.error('Error incrementing item quantity:', error);
        showNotification('Error incrementing item quantity', 'error');
    });
}

// Function to decrement cart item quantity
function decrementCartItem(index) {
    fetch('update-cart-quantity.php', {
        method: 'POST',
        headers: { 
            'Content-Type': 'application/json',
            'X-CSRFToken': getCsrfToken()
        },
        body: JSON.stringify({ index: index, action: 'decrement' })
    })
    .then(response => response.json())
    .then(data => {
        if (data.success) {
            loadCart();
        } else {
            showNotification(data.message, 'error');
        }
    })
    .catch(error => {
        console.error('Error decrementing item quantity:', error);
        showNotification('Error decrementing item quantity', 'error');
    });
}

// ── Load cart from server ─────────────────────────────────────────────────────
function loadCart() {
    fetch('get-cart.php')
        .then(response => {
            if (!response.ok) {
                // Check if redirected to login (HTML response instead of JSON)
                if (response.headers.get('content-type') && response.headers.get('content-type').includes('text/html')) {
                    window.location.href = 'login.php';
                    return;
                }
                throw new Error('Network response was not ok');
            }
            return response.json();
        })
        .then(data => {
            if (data) {
                cart = data.items || [];
                updateCart();
            }
        })
        .catch(function (error) {
            console.error('Error loading cart:', error);
        });
}

// ── Render cart table ─────────────────────────────────────────────────────────
function updateCart() {
    const cartItemsElement = document.getElementById('cartItems');
    const cartTotalElement = document.getElementById('cartTotal');
    
    if (!cartItemsElement || !cartTotalElement) {
        return; // Elements don't exist (user not logged in)
    }
    
    let total = 0;
    cartItemsElement.innerHTML = '';

    cart.forEach((item, index) => {
        const row = document.createElement('tr');
        row.innerHTML = `
            <td>${item.item_name}</td>
            <td>₱ ${item.item_price.toFixed(2)}</td>
            <td>
                <button onclick="decrementCartItem(${index})" style="padding: 2px 8px;">-</button>
                <span>${item.quantity}</span>
                <button onclick="incrementCartItem(${index})" style="padding: 2px 8px;">+</button>
            </td>
            <td><button onclick="removeFromCart(${index})" style="background-color: #dc3545; color: white; border: none; padding: 2px 8px;">X</button></td>
        `;
        cartItemsElement.appendChild(row);
        total += item.item_price * item.quantity;
    });

    cartTotalElement.textContent = '₱ ' + total.toFixed(2);
}

// ── Wire up UI once DOM is ready ──────────────────────────────────────────────
document.addEventListener('DOMContentLoaded', function () {

    // Only initialise cart for logged-in users
    if (!window.isUserLoggedIn) return;

    // Load cart items on page load
    loadCart();

    // Open cart sidebar
    const openCartBtn = document.getElementById('openCart');
    const cartEl = document.querySelector('.cart');
    if (openCartBtn && cartEl) {
        openCartBtn.addEventListener('click', function (e) {
            e.preventDefault();
            cartEl.classList.add('open');
        });
    }

    // Close cart sidebar
    const closeCartBtn = document.getElementById('closeCart');
    if (closeCartBtn && cartEl) {
        closeCartBtn.addEventListener('click', function () {
            cartEl.classList.remove('open');
        });
    }

    // Checkout button
    const checkoutBtn = document.getElementById('checkOut');
    if (checkoutBtn) {
        checkoutBtn.addEventListener('click', function () {
            if (cart.length === 0) {
                showNotification('You need to add an item first!', 'error');
            } else {
                const btn = this;
                btn.disabled = true;
                btn.textContent = 'Processing...';

                fetch('checkout.php', {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json',
                        'X-CSRFToken': getCsrfToken()
                    },
                    body: JSON.stringify({ cart: cart, totalPrice: cart.reduce((sum, item) => sum + (item.item_price * item.quantity), 0) })
                })
                .then(function (response) {
                    if (!response.ok) {
                        throw new Error('Server error ' + response.status);
                    }
                    return response.json();
                })
                .then(function (data) {
                    if (data.success) {
                        window.location.href = data.redirect_url || 'delivery.php';
                    } else {
                        showNotification(data.message || 'Checkout failed. Please try again.', 'error');
                        btn.disabled = false;
                        btn.textContent = 'Checkout';
                    }
                })
                .catch(function (err) {
                    console.error('Checkout error:', err);
                    showNotification('Checkout failed: ' + err.message + '. Please try again.', 'error');
                    btn.disabled = false;
                    btn.textContent = 'Checkout';
                });
            }
        });
    }
});
