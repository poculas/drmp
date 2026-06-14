let openCartBtn = document.getElementById('openCart');
let closeCartBtn = document.getElementById('closeCart');
let body = document.querySelector('body');
let cartElement = document.querySelector('.cart');
let checkOut = document.getElementById('checkOut');
var cart = [];
var totalPrice = 0.00;

document.addEventListener('DOMContentLoaded', loadCart);

// Function to show notification popup
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

    // Set color based on type
    if (type === 'success') {
        notification.style.backgroundColor = '#28a745';
    } else if (type === 'error') {
        notification.style.backgroundColor = '#dc3545';
    } else {
        notification.style.backgroundColor = '#17a2b8';
    }

    // Add to body
    document.body.appendChild(notification);

    // Remove after 3 seconds
    setTimeout(() => {
        notification.remove();
    }, 3000);
}

// Function to add item to cart
function addToCart(name, price, quantity) {
    // Check if user is logged in
    if (!window.isUserLoggedIn) {
        window.location.href = '/login.php';
        return;
    }
    
    const item = { name: name, price: price, quantity: quantity };

    fetch('add-to-cart.php', {
        method: 'POST',
        headers: { 
            'Content-Type': 'application/json',
            'X-CSRFToken': getCookie('csrftoken')
        },
        body: JSON.stringify(item)
    })
    .then(response => {
        if (!response.ok) {
            // Check if redirected to login (HTML response instead of JSON)
            if (response.headers.get('content-type') && response.headers.get('content-type').includes('text/html')) {
                window.location.href = '/login.php';
                return;
            }
            throw new Error('Network response was not ok');
        }
        return response.json();
    })
    .then(data => {
        if (data) {
            showNotification(data.message, 'success');
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

// Function to remove item from cart
function removeFromCart(index) {
    fetch('remove-from-cart.php', {
        method: 'POST',
        headers: { 
            'Content-Type': 'application/json',
            'X-CSRFToken': getCookie('csrftoken')
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
            'X-CSRFToken': getCookie('csrftoken')
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
            'X-CSRFToken': getCookie('csrftoken')
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

// Function to load the cart
function loadCart() {
    fetch('get-cart.php')
        .then(response => {
            if (!response.ok) {
                // Check if redirected to login (HTML response instead of JSON)
                if (response.headers.get('content-type') && response.headers.get('content-type').includes('text/html')) {
                    window.location.href = '/login.php';
                    return;
                }
                throw new Error('Network response was not ok');
            }
            return response.json();
        })
        .then(data => {
            if (data) {
                cart = data.items;
                updateCart();
            }
        })
        .catch(error => console.error('Error loading cart:', error));
}

// Function to update the cart display
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

    cartTotalElement.textContent = `₱ ${total.toFixed(2)}`;
}

// Event listeners for opening and closing cart
if (openCartBtn) {
    openCartBtn.addEventListener('click', () => {
        cartElement.classList.add('open');
    });
}

if (closeCartBtn) {
    closeCartBtn.addEventListener('click', () => {
        cartElement.classList.remove('open');
    });
}

// Checkout function
if (checkOut) {
    checkOut.addEventListener('click', () => {
        if (cart.length === 0) {
            showNotification('You need to add an item first!', 'error');
        } else {
            fetch('checkout.php', {
                method: 'POST',
                headers: { 
                    'Content-Type': 'application/json',
                    'X-CSRFToken': getCookie('csrftoken')
                },
                body: JSON.stringify({ cart: cart, totalPrice: totalPrice })
            })
            .then(response => {
                if (!response.ok) throw new Error('Network response was not ok');
                return response.json();
                
            })
            .then(data => {
                if (data.success) window.location.href = 'pickup.php';
                else showNotification('Checkout failed: ' + data.message, 'error');
            })
            .catch(error => {
                console.error('Error during checkout:', error);
                showNotification('Error during checkout', 'error');
            });
        }
    });
}