<?php

session_start();

if(!isset($_SESSION['is_logged_in'])){
    $_SESSION['is_logged_in'] = false;
}

$conn = mysqli_connect("localhost", "root", "", "user_registration");

if (!$conn) {
    die("Connection failed: " . mysqli_connect_error());
}

if ($_SERVER['REQUEST_METHOD'] == 'POST' && isset($_POST['pay'])) {

    $user_id = $_SESSION['user_id'];
    $session_id = $_SESSION['session_id'];
    $total_price = $_SESSION['total_price'];

    $order_date = date('Y-m-d H:i:s');
    $house = mysqli_real_escape_string($conn, $_POST['houseNumber']);
    $street = mysqli_real_escape_string($conn, $_POST['street']);
    $barangay = mysqli_real_escape_string($conn, $_POST['barangay']);
    $postal = mysqli_real_escape_string($conn, $_POST['postalCode']);
    $city = mysqli_real_escape_string($conn, $_POST['city']);

    $query = "INSERT INTO receipts (user_id, session_id, order_date, total_price, housenumber, streetname, barangay, postalcode, city) VALUES ('$user_id', '$session_id', '$order_date', '$total_price', '$house', '$street', '$barangay', '$postal', '$city')";

    if (mysqli_query($conn, $query)) {
        header("Location: receipt.php");
        exit();

    } else {
        echo "Error: " . $query . "<br>" . mysqli_error($conn);
    }
}
?>

<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Dough Re Mi Patisserie - Billing Information</title>
    <link rel="stylesheet" href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0-alpha1/dist/css/bootstrap.min.css">
    <link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.0.0-beta3/css/all.min.css">
    <link rel ="stylesheet" href="styles.css">
    <link rel="icon" href="images/tab.png">
    <style>
        #delivery-info {
    margin: auto;
    padding: 20px;
    width: 100%;
    max-width: 500px;
}

.delivery-container {
    background-color: #fff;
    border-radius: 15px;
    margin-top:10%;
    padding: 30px 40px;
    box-shadow: 0 0 20px rgba(0, 0, 0, 0.2);
}

h2 {
    text-align: center;
    color: rgb(46, 33, 2);
    margin-bottom: 20px;
}

label {
    display: block;
    margin-bottom: 5px;
    font-weight: bold;
    color: #333;
}

input[type="text"],
input[type="number"],
select {
    width: 100%;
    padding: 10px;
    margin-bottom: 15px;
    border: 1px solid #ccc;
    border-radius: 5px;
}

.total-container {
    margin-bottom: 20px;
    text-align: center;
    font-weight: bold;
    color: rgb(46, 33, 2);
}

.pay-btn {
    background-color: rgb(121, 65, 28);
    color: #fff;
    padding: 12px;
    width: 100%;
    border: none;
    border-radius: 10px;
    cursor: pointer;
    font-weight: bold;
    font-size: 16px;
}

.pay-btn:hover {
    background-color: rgb(150, 80, 30);
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
                    <li class="nav-item"><a class="nav-link" href="menu.php">Menu</a></li>
                    <li class="nav-item"><a class="nav-link" href="aboutus.php">About Us</a></li>
                    <li class="nav-item"><a class="nav-link active" href="#" id="openCart">Cart</a></li>
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

    <section id="delivery-info">
        <div class="delivery-container">
            <h2>Billing Information</h2>
            <form id="delivery" action="delivery.php" method="POST">
                <input type="hidden" name="pay" value="1">
                <label for="house">House/Unit No.:</label>
                <input type="number" id="house" name="houseNumber" required>

                <label for="street">Street:</label>
                <input type="text" id="street" name="street" required>

                <label for="barangay">Barangay:</label>
                <input type="text" id="barangay" name="barangay" required>

                <label for="city">City:</label>
                <input type="text" id="city" name="city" required>

                <label for="postalCode">Postal Code:</label>
                <input type="number" id="postalCode" pattern="\d*" name="postalCode" required>

                <label for="paymentMethod">Payment Method:</label>
                <select id="paymentMethod" name="paymentMethod" required>
                    <option value="" disabled selected>Select a payment method</option>

                    <option value="Gcash">Gcash</option>
                    <option value="PayMaya">PayMaya</option>
                    <option value="BDO">BDO</option>
                    <option value="Cash on delivery">Cash on delivery</option>
                </select>

                <div class="total-container">
                    <p id="cartTotal">TOTAL: ₱<?php echo htmlspecialchars($_SESSION['total_price']); ?></p>
                </div>

                <button type="submit" class="pay-btn" id="payNow" name="payNow">PAY NOW</button>
            </form>
        </div>
    </section>
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
</body>
</html>