<?php
session_start();

if(!isset($_SESSION['is_logged_in'])){
    $_SESSION['is_logged_in'] = false;
}
?>

<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Dough Re Mi Patisserie</title>
    <link rel="stylesheet" href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0-alpha1/dist/css/bootstrap.min.css">
    <link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.0.0-beta3/css/all.min.css">
    <link rel ="stylesheet" href="styles.css">
    <link rel="icon" href="images/tab.png">
    <style>
        .hero-section video {
            width: 100%;
            height: 100%;
            object-fit: cover;
        }
        .hero-content {
            position: absolute;
            top: 50%;
            left: 50%;
            transform: translate(-50%, -50%);
            text-align: center;
            color: white;
        }
        .hero-content img {
            height: 80px;
            margin-bottom: 1rem;
        }
        #menuLogo{
            height:200px;
        }
        .card {
            transition: transform 0.3s;
        }
        .card:hover {
            transform: translateY(-5px);
        }
        .card-img-top {
            height: 200px;
            object-fit: cover;
        }
        .btn-primary {
            background-color: #8b4513;
            border-color: #8b4513;
        }
        .btn-primary:hover {
            background-color: #a0522d;
            border-color: #a0522d;
        }
        .cart {
            position: fixed;
            top: 0;
            right: -400px;
            width: 400px;
            height: 100%;
            background-color: white;
            box-shadow: -2px 0 5px rgba(0, 0, 0, 0.1);
            transition: right 0.3s ease;
            z-index: 1000;
        }
        .cart.open {
            right: 0;
        }
        .cart-header {
            background-color: #8b4513;
            color: white;
            padding: 1rem;
            text-align: center;
        }
        .cart-body {
            padding: 1rem;
        }

        .cart-footer {
            position: absolute;
            bottom: 0;
            left: 0;
            width: 100%;
            background-color: #8b4513;
            color: white;
            padding: 1rem;
            text-align: center;
        }
        
    </style>
</head>
<body>
    <nav class="navbar navbar-expand-lg navbar-dark">
        <div class="container">
            <a class="navbar-brand" href="index.php"><img src="../images/logoWhite.png?v=2" alt="Dough Re Mi Patisserie"></a>
            <button class="navbar-toggler" type="button" data-bs-toggle="collapse" data-bs-target="#navbarNav" aria-controls="navbarNav" aria-expanded="false" aria-label="Toggle navigation">
                <span class="navbar-toggler-icon"></span>
            </button>
            <div class="collapse navbar-collapse" id="navbarNav">
                <ul class="navbar-nav ms-auto">
                    <li class="nav-item"><a class="nav-link" href="index.php">Home</a></li>
                    <li class="nav-item"><a class="nav-link active" href="menu.php">Menu</a></li>
                    <li class="nav-item"><a class="nav-link" href="aboutus.php">About Us</a></li>
                    <li class="nav-item"><a class="nav-link" href="#" id="openCart">Cart</a></li>
                    <?php if ($_SESSION['is_logged_in']): ?>
                      <li class="nav-item"><a class="nav-link" href="logout.php">Log out</a></li>
                      <li>Welcome, <?php echo htmlspecialchars($_SESSION['user_id']); ?></li>  
                    <?php else: ?>
                    <li class="nav-item"><a class="nav-link" href="login.php">Log in</a></li>
                    <?php endif; ?>
                </ul>
            </div>
        </div>
    </nav>

    <div class="hero-section">
        <video autoplay loop muted plays-inline>
            <source src="media/AboutBread.mp4" type="video/mp4">
        </video>
        <div class="hero-content">
            <img id="menuLogo" src="images/tab.png" alt="Dough Re Mi Patisserie Logo">
            <h1 class="display-4">Dough Re Mi Patisserie</h1>
            <p class="lead">So fast, so good! The home of freshly baked French pastries.</p>
        </div>
    </div>

    <div class="container my-5">
        <h2 class="text-center mb-4">Our Menu</h2>
        <div class="row g-4">
            <div class="col-md-4">
                <div class="card h-100">
                    <img src="images/croissant.png" class="card-img-top" alt="Classic Croissant">
                    <div class="card-body">
                        <h5 class="card-title">Classic Croissant</h5>
                        <p class="card-text">PHP 40</p>
                        <div class="input-group mb-3" id="qty">
                        <button class="input-group-text decrement-btn" onclick="decrement()">-</button>
                        <input type="text" class="form-control text-center product_quantity bg-white" id="product_quantity" value="1">
                        <button class="input-group-text increment-btn" onclick="increment()">+</button>
                    </div>
                        <button class="btn btn-primary w-100" onclick="addToCart('Classic Croissant',40.00,document.getElementById('product_quantity').value)">ADD TO CART</button>
                    </div>
                </div>
            </div>
            <div class="col-md-4">
                <div class="card h-100">
                    <img src="images/baguette.png" class="card-img-top" alt="Medium Baguette">
                    <div class="card-body">
                        <h5 class="card-title">Medium Baguette</h5>
                        <p class="card-text">PHP 89</p>
                        <div class="input-group mb-3" id="qty">
                        <button class="input-group-text decrement-btn" onclick="decrement1()">-</button>
                        <input type="text" class="form-control text-center product_quantity1 bg-white" id="product_quantity1" value="1">
                        <button class="input-group-text increment-btn" onclick="increment1()">+</button>
                    </div>
                        <button class="btn btn-primary w-100" onclick="addToCart('Medium Baguette', 89.00)">ADD TO CART</button>
                    </div>
                </div>
            </div>
           
            <div class="col-md-4">
                <div class="card h-100">
                    <img src="images/Strawberry Macaroons.png" class="card-img-top" alt="Strawberry Macaroons">
                    <div class="card-body">
                        <h5 class="card-title">Strawberry Macaroons</h5>
                        <p class="card-text">PHP 30</p>
                        <div class="input-group mb-3" id="qty">
                        <button class="input-group-text decrement-btn" onclick="decrement2()">-</button>
                        <input type="text" class="form-control text-center product_quantity2 bg-white" id="product_quantity2" value="1">
                        <button class="input-group-text increment-btn" onclick="increment2()">+</button>
                    </div>
                        <button class="btn btn-primary w-100" onclick="addToCart('Strawberry Macaroons', 30.00)">ADD TO CART</button>
                    </div>
                </div>
            </div>
            <div class="col-md-4">
                <div class="card h-100">
                    <img src="images/Eclair.png" class="card-img-top" alt="Eclair">
                    <div class="card-body">
                        <h5 class="card-title">Eclair</h5>
                        <p class="card-text">PHP 25</p>
                        <div class="input-group mb-3" id="qty">
                        <button class="input-group-text decrement-btn" onclick="decrement3()">-</button>
                        <input type="text" class="form-control text-center product_quantity3 bg-white" id="product_quantity3" value="1">
                        <button class="input-group-text increment-btn" onclick="increment3()">+</button>
                    </div>
                        <button class="btn btn-primary w-100" onclick="addToCart('Eclair', 25.00)">ADD TO CART</button>
                    </div>
                </div>
            </div>
            <div class="col-md-4">
                <div class="card h-100">
                    <img src="images/baguette.png" class="card-img-top" alt="Medium Baguette">
                    <div class="card-body">
                        <h5 class="card-title">Medium Baguette</h5>
                        <p class="card-text">PHP 89</p>
                        <div class="input-group mb-3" id="qty">
                        <button class="input-group-text decrement-btn" onclick="decrement4()">-</button>
                        <input type="text" class="form-control text-center product_quantity4 bg-white" id="product_quantity4" value="1">
                        <button class="input-group-text increment-btn" onclick="increment4()">+</button>
                        </div>
                        <button class="btn btn-primary w-100" onclick="addToCart('Medium Baguette',  89.00)">ADD TO CART</button>
                    </div>
                </div>
            </div>
            
            <div class="col-md-4">
                <div class="card h-100">
                    <img src="images/Pan au Chocolat.png" class="card-img-top" alt="Pan au Chocolat">
                    <div class="card-body">
                        <h5 class="card-title">Pan au Chocolat</h5>
                        <p class="card-text">PHP 45</p>
                        <div class="input-group mb-3" id="qty">
                        <button class="input-group-text decrement-btn" onclick="decrement5()">-</button>
                        <input type="text" class="form-control text-center product_quantity5 bg-white" id="product_quantity5" value="1">
                        <button class="input-group-text increment-btn" onclick="increment5()">+</button>
                    </div>
                        <button class="btn btn-primary w-100" onclick="addToCart('Pan au Chocolat', 45.00)">ADD TO CART</button>
                    </div>
                </div>
            </div>
            <div class="col-md-4">
                <div class="card h-100">
                    <img src="images/Strawberry Macaroons.png" class="card-img-top" alt="Strawberry Macaroons">
                    <div class="card-body">
                        <h5 class="card-title">Strawberry Macaroons</h5>
                        <p class="card-text">PHP 30</p>
                        <div class="input-group mb-3" id="qty">
                        <button class="input-group-text decrement-btn" onclick="decrement6()">-</button>
                        <input type="text" class="form-control text-center product_quantity6 bg-white" id="product_quantity6" value="1">
                        <button class="input-group-text increment-btn" onclick="increment6()">+</button>
                    </div>
                        <button class="btn btn-primary w-100" onclick="addToCart('Strawberry Macaroons', 30.00)">ADD TO CART</button>
                    </div>
                </div>
            </div>
            <div class="col-md-4">
                <div class="card h-100">
                    <img src="images/Eclair.png" class="card-img-top" alt="Eclair">
                    <div class="card-body">
                        <h5 class="card-title">Eclair</h5>
                        <p class="card-text">PHP 25</p>
                        <div class="input-group mb-3" id="qty">
                        <button class="input-group-text decrement-btn" onclick="decrement7()">-</button>
                        <input type="text" class="form-control text-center product_quantity7 bg-white" id="product_quantity7" value="1">
                        <button class="input-group-text increment-btn" onclick="increment7()">+</button>
                    </div>
                        <button class="btn btn-primary w-100" onclick="addToCart('Eclair', 25.00)">ADD TO CART</button>
                    </div>
                </div>
            </div>
            <div class="col-md-4">
                <div class="card h-100">
                    <img src="images/Paris-Brest.png" class="card-img-top" alt="Paris-Brest">
                    <div class="card-body">
                        <h5 class="card-title">Paris-Brest</h5>
                        <p class="card-text">PHP 129</p>
                        <div class="input-group mb-3" id="qty">
                        <button class="input-group-text decrement-btn" onclick="decrement8()">-</button>
                        <input type="text" class="form-control text-center product_quantity8 bg-white" id="product_quantity8" value="1">
                        <button class="input-group-text increment-btn" onclick="increment8()">+</button>
                    </div>
                        <button class="btn btn-primary w-100" onclick="addToCart('Paris-Brest', 129.00)">ADD TO CART</button>
                    </div>
                </div>
            </div>
 
        </div>
    </div>

    <div class="cart">
        <div class="cart-header">
            <img src="../images/logoWhite.png?v=2" alt="Dough Re Mi Patisserie Logo" style="height: 40px;">
        </div>
        <div class="cart-body">
            <table class="table">
                <thead>
                    <tr>
                        <th>Item</th>
                         <th>Price</th>
                        <th>Quantity</th>
                       
                    </tr>
                </thead>
                <tbody id="cartItems"></tbody>
            </table>
            <div class="d-flex justify-content-between">
                <strong>Total:</strong>
                <span id="cartTotal">₱ 0.00</span>
            </div>
        </div>
        <div class="cart-footer">
            <button class="btn btn-light w-100 mb-2" id="checkOut">Checkout</button>
            <button id="closeCart" class="btn btn-outline-light w-100">Close</button>
        </div>
    </div>

    <footer class="py-4 mt-5">
        <div class="container">
            <div class="row">
                <div class="col-md-4">
                    <h5>Quick Links</h5>
                    <ul class="list-unstyled">
                    <li><a href="index.php" class="text-white">Home</a></li>
                        <li><a href="menu.php" class="text-white">Menu</a></li>
                        <li><a href="aboutus.php" class="text-white">About us</a></li>
                        <li><a href="login.php" class="text-white">Log in</a></li>
                    </ul>
                </div>
                <div class="col-md-4">
                    <h5>Follow Us</h5>
                    <a href="https://www.facebook.com/" class="text-white me-3"><i class="fab fa-facebook-f"></i></a>
                    <a href="https://twitter.com/" class="text-white me-3"><i class="fab fa-twitter"></i></a>
                    <a href="https://www.instagram.com/" class="text-white"><i class="fab fa-instagram"></i></a>
                </div>
                <div class="col-md-4">
                    <p>© 2024, Dough Re Mi Patisserie Online Quiapo Manila</p>
                    <p>Dough Re Mi Patisserie Online</p>
                </div>
            </div>
        </div>
    </footer>
    <script src="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0-alpha1/dist/js/bootstrap.bundle.min.js"></script>
    <script src="scripts/menu.js"></script>
    <script>
        function increment() {
    const quantityInput = document.getElementById('product_quantity');
    let quantity = parseInt(quantityInput.value);
    quantity++;
    quantityInput.value = quantity;
  }

  function decrement() {
    const quantityInput = document.getElementById('product_quantity');
    let quantity = parseInt(quantityInput.value);
    if (quantity > 1) {
      quantity--;
    }
    quantityInput.value = quantity;
  }

         function increment1() {
    const quantityInput = document.getElementById('product_quantity1');
    let quantity = parseInt(quantityInput.value);
    quantity++;
    quantityInput.value = quantity;
  }

  function decrement1() {
    const quantityInput = document.getElementById('product_quantity1');
    let quantity = parseInt(quantityInput.value);
    if (quantity > 1) {
      quantity--;
    }
    quantityInput.value = quantity;
  }

  function increment2() {
    const quantityInput = document.getElementById('product_quantity2');
    let quantity = parseInt(quantityInput.value);
    quantity++;
    quantityInput.value = quantity;
  }

  function decrement2() {
    const quantityInput = document.getElementById('product_quantity2');
    let quantity = parseInt(quantityInput.value);
    if (quantity > 1) {
      quantity--;
    }
    quantityInput.value = quantity;
  }

  function increment3() {
    const quantityInput = document.getElementById('product_quantity3');
    let quantity = parseInt(quantityInput.value);
    quantity++;
    quantityInput.value = quantity;
  }

  function decrement3() {
    const quantityInput = document.getElementById('product_quantity3');
    let quantity = parseInt(quantityInput.value);
    if (quantity > 1) {
      quantity--;
    }
    quantityInput.value = quantity;
  }

  function increment4() {
    const quantityInput = document.getElementById('product_quantity4');
    let quantity = parseInt(quantityInput.value);
    quantity++;
    quantityInput.value = quantity;
  }

  function decrement4() {
    const quantityInput = document.getElementById('product_quantity4');
    let quantity = parseInt(quantityInput.value);
    if (quantity > 1) {
      quantity--;
    }
    quantityInput.value = quantity;
  }

  function increment5() {
    const quantityInput = document.getElementById('product_quantity5');
    let quantity = parseInt(quantityInput.value);
    quantity++;
    quantityInput.value = quantity;
  }

  function decrement5() {
    const quantityInput = document.getElementById('product_quantity5');
    let quantity = parseInt(quantityInput.value);
    if (quantity > 1) {
      quantity--;
    }
    quantityInput.value = quantity;
  }

  function increment6() {
    const quantityInput = document.getElementById('product_quantity6');
    let quantity = parseInt(quantityInput.value);
    quantity++;
    quantityInput.value = quantity;
  }

  function decrement6() {
    const quantityInput = document.getElementById('product_quantity6');
    let quantity = parseInt(quantityInput.value);
    if (quantity > 1) {
      quantity--;
    }
    quantityInput.value = quantity;
  }

  function increment7() {
    const quantityInput = document.getElementById('product_quantity7');
    let quantity = parseInt(quantityInput.value);
    quantity++;
    quantityInput.value = quantity;
  }

  function decrement7() {
    const quantityInput = document.getElementById('product_quantity7');
    let quantity = parseInt(quantityInput.value);
    if (quantity > 1) {
      quantity--;
    }
    quantityInput.value = quantity;
  }

  function increment8() {
    const quantityInput = document.getElementById('product_quantity8');
    let quantity = parseInt(quantityInput.value);
    quantity++;
    quantityInput.value = quantity;
  }

  function decrement8() {
    const quantityInput = document.getElementById('product_quantity8');
    let quantity = parseInt(quantityInput.value);
    if (quantity > 1) {
      quantity--;
    }
    quantityInput.value = quantity;
  }

    </script>
</body>
</html>