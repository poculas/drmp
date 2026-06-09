let openCartBtn = document.getElementById('openCart');
let closeCartBtn = document.getElementById('closeCart');
let body = document.querySelector('body');
let cartElement = document.querySelector('.cart');
let checkOut = document.getElementById('checkOut');
var cart = [];
var totalPrice = 0.00;

document.addEventListener('DOMContentLoaded', loadCart);

// Function to add item to cart
function addToCart(name, price) {
    const item = { name: name, price: price };

    fetch('add-to-cart.php', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(item)
    })
    .then(response => response.json())
    .then(data => {
        alert(data.message);
        loadCart();
    })
    .catch(error => console.error('Error adding item to cart:', error));
}

// Function to remove item from cart
function removeFromCart(index) {
    fetch('remove-from-cart.php', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ index: index })
    })
    .then(response => response.json())
    .then(data => {
        alert(data.message);
        loadCart();
    })
    .catch(error => console.error('Error removing item from cart:', error));
}

// Function to load the cart
function loadCart() {
    fetch('get-cart.php')
        .then(response => response.json())
        .then(data => {
            cart = data.items;
            updateCart();
        })
        .catch(error => console.error('Error loading cart:', error));
}

// Function to update the cart display
function updateCart() {
    const cartItemsElement = document.getElementById('cartItems');
    const cartTotalElement = document.getElementById('cartTotal');
    let total = 0;

    cartItemsElement.innerHTML = '';

    cart.forEach((item, index) => {
        const row = document.createElement('tr');
        row.innerHTML = `
            <td>${item.item_name}</td>
            <td>₱ ${item.item_price.toFixed(2)}</td>
            <td></td>
            <td><button onclick="removeFromCart(${index})">X</button></td>
        `;
        cartItemsElement.appendChild(row);
        total += item.item_price;
    });

    cartTotalElement.textContent = `₱ ${total.toFixed(2)}`;
}

// Event listeners for opening and closing cart
openCartBtn.addEventListener('click', () => {
    cartElement.classList.add('open');
});

closeCartBtn.addEventListener('click', () => {
    cartElement.classList.remove('open');
});

// Checkout function
checkOut.addEventListener('click', () => {
    if (cart.length === 0) {
        alert('You need to add an item first!');
    } else {
        fetch('checkout.php', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ cart: cart, totalPrice: totalPrice })
        })
        .then(response => {
            if (!response.ok) throw new Error('Network response was not ok');
            return response.json();
            
        })
        .then(data => {
            if (data.success) window.location.href = 'delivery.php';
            else alert('Checkout failed: ' + data.message);
        })
        .catch(error => console.error('Error during checkout:', error));
    }
});