<?php
session_start();


if(!isset($_SESSION['is_logged_in'])){
    $_SESSION['is_logged_in'] = false;
}

$conn = mysqli_connect("localhost", "root", "", "user_registration");

if (!$conn) {
    die("Connection failed: " . mysqli_connect_error());
}

$login_successful = false; 
$error_message = ""; 

if (isset($_POST['login'])) {
    $email = mysqli_real_escape_string($conn, $_POST['email']);
    $password = $_POST['password'];

    $query = "SELECT * FROM users WHERE email='$email'";
    $result = mysqli_query($conn, $query);
    
    if ($result && mysqli_num_rows($result) > 0) {
        $user = mysqli_fetch_assoc($result);

        if (password_verify($password, $user['password'])) {
            $login_successful = true; 
            $_SESSION['user_id'] = $user['firstname'] . ' ' . $user['lastname'];
            $_SESSION['email'] = $email;
            $_SESSION['customer_id'] = $user['customer_id'];
            $_SESSION['is_logged_in'] = isset($_SESSION['user_id']);
        } else {
            $error_message = "Incorrect Username or Password!"; 
        }
    } else {
        $error_message = "Incorrect Username or Password!"; 
    }
    
    mysqli_close($conn);
}
?>

<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Dough Re Mi Patisserie</title>
    <link
      href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0-alpha1/dist/css/bootstrap.min.css"
      rel="stylesheet"
    />
    <link
      rel="stylesheet"
      href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.0.0-beta3/css/all.min.css"
    />
    <link rel ="stylesheet" href="styles.css">
    <link rel="icon" href="images/tab.png">

    <script>
        window.onload = function() {
            <?php if ($login_successful): ?>
                alert("Login successful!");
                window.location.href = "index.php"; 
            <?php elseif ($error_message): ?>
                alert("<?php echo addslashes($error_message); ?>"); 
            <?php endif; ?>
        }
    </script>
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
                    <?php if ($_SESSION['is_logged_in']): ?>
                      <li class="nav-item"><a class="nav-link" href="logout.php">Log out</a></li>
                      <li>Welcome, <?php echo htmlspecialchars($_SESSION['user_id']); ?></li>  
                    <?php else: ?>
                    <li class="nav-item"><a class="nav-link active" href="login.php">Log in</a></li>
                    <?php endif; ?>
                </ul>
            </div>
        </div>
    </nav>
    <section>
        <div class="registration">
            <h1>Log in</h1>
            <p>New user? <a href="signup.php">Sign up</a> instead</p>

            <form id="login" method="POST" action="login.php">
                
                <label for="email"><h4>Email:</h4></label>
                <input type="email" name="email" id="email" required>
                <br><br><br>
                <label for="password"><h4>Password:</h4></label>
                <input type="password" name="password" id="password" required>
                <button type="submit" name="login" id="submit"><h3>Log in</h3></button>
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