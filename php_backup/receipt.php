<?php

session_start();

if(!isset($_SESSION['is_logged_in'])){
    $_SESSION['is_logged_in'] = false;
}

$conn = mysqli_connect("localhost", "root", "", "user_registration");

if (!$conn) {
    die("Connection failed: " . mysqli_connect_error());
}

$email = $_SESSION['email'];
$customer_query = "SELECT * FROM users WHERE email = '$email'";
$customer_result = mysqli_query($conn, $customer_query);
$customer_data = mysqli_fetch_assoc($customer_result);

$session_id = $_SESSION['session_id'];
$address_query = "SELECT * FROM receipts WHERE session_id = '$session_id'";
$address_result = mysqli_query($conn, $address_query);
$address_data = mysqli_fetch_assoc($address_result);

$order_query = "SELECT item_name, item_price FROM orders WHERE session_id = '$session_id'";
$order_result = mysqli_query($conn, $order_query);
?>

<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Dough Re Mi Patisserie - Receipt</title>
    <link rel ="stylesheet" href="styles.css">
    <link rel="icon" href="images/tab.png">
    <link rel="stylesheet" href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0-alpha1/dist/css/bootstrap.min.css">
    <link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.0.0-beta3/css/all.min.css">
 <style>

h1, h2{
    text-align: center;
    font-size: 30px;
    }
table{
    background-color: white;
    height:250px;
    width: 500px;
    margin: 0 auto;
}

td,th{
    padding: 15px;
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
    <section>
        <br>
        <h1>Online Receipt</h1>
        <table id="customerInfo">
            <tr>
                <th colspan="2"><h2>Customer Details</h2></th>
            </tr>
            <tr>
                <td><b>First Name:</b></td>
                <td><?php echo htmlspecialchars($customer_data['firstname']); ?></td>
            </tr>
            <tr>
                <td><b>Last Name:</b></td>
                <td><?php echo htmlspecialchars($customer_data['lastname']); ?></td>
            </tr>
            <tr>
                <td><b>Email:</b></td>
                <td><?php echo htmlspecialchars($customer_data['email']); ?></td>
            </tr>
            <tr>
                <td><b>Contact Number:</b></td>
                <td><?php echo htmlspecialchars($customer_data['contactnumber']); ?></td>
            </tr>
            <tr>
                <td><b>House Number</b></td>
                <td><?php echo htmlspecialchars($address_data['housenumber']); ?></td>
            </tr>
            <tr>
                <td><b>Street Name:</b></td>
                <td><?php echo htmlspecialchars($address_data['streetname']); ?></td>
            </tr>
            <tr>
                <td><b>Barangay:</b></td>
                <td><?php echo htmlspecialchars($address_data['barangay']); ?></td>
            </tr>
            <tr>
                <td><b>Postal code:</b></td>
                <td><?php echo htmlspecialchars($address_data['postalcode']); ?></td>
            </tr>
            <tr>
                <td><b>City:</b></td>
                <td><?php echo htmlspecialchars($address_data['city']); ?></td>
            </tr>
        </table>
<br>
        <table id="orderInfo">
            <tr>
                <th colspan="2"><h2>Order Details</h2></th>
            </tr>
            <tr>
                <th>Item</th>
                <th>Price</th>
            </tr>
            <?php
            // Check if there are any orders
            if (mysqli_num_rows($order_result) > 0) {
                // Loop through each order and display it
                while ($order_data = mysqli_fetch_assoc($order_result)) {
                    echo '<tr>';
                    echo '<td>' . htmlspecialchars($order_data['item_name']) . '</td>';
                    echo '<td>₱' . number_format($order_data['item_price'], 2) . '</td>';
                    echo '</tr>';
                }
            } else {
                echo '<tr><td colspan="2">No order details found.</td></tr>';
            }
            ?>
            <tr>
                <td><h3>Total Price: </h3></td>
                <td>₱<?php echo htmlspecialchars($address_data['total_price']); ?></td>
            </tr>
        </table>
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