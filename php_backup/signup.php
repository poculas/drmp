<?php
session_start();

if(!isset($_SESSION['is_logged_in'])){
    $_SESSION['is_logged_in'] = false;
}

$conn = mysqli_connect("localhost", "root", "", "user_registration");

if (!$conn) {
    die("Connection failed: " . mysqli_connect_error());
}

$signup_successful = false; 
$error_message = "";

if ($_SERVER['REQUEST_METHOD'] == 'POST' && isset($_POST['register'])) {
    $firstname = mysqli_real_escape_string($conn, $_POST['firstname']);
    $lastname = mysqli_real_escape_string($conn, $_POST['lastname']);
    $number = mysqli_real_escape_string($conn, $_POST['contactnumber']);
    $email = mysqli_real_escape_string($conn, $_POST['email']);
    $password = password_hash($_POST['password'], PASSWORD_BCRYPT);
    $pass = $_POST['password'];
    $confirmpass = $_POST['confirmpassword'];

    $checkNumberQuery = "SELECT * FROM users WHERE contactnumber='$number'";
    $numresult = mysqli_query($conn, $checkNumberQuery);

    if (mysqli_num_rows($numresult) > 0) {
        $error_message .= "Error: Contact number already registered. Please use a different number.\n";
    }

    if (!preg_match('/^\d{11}$/', $number)) {
        $error_message .= "Error: Phone number must be exactly 11 digits.";
    }

    if (!filter_var($email, FILTER_VALIDATE_EMAIL)) {
        $error_message .= "Error: Invalid email format.";
    }

    $checkEmailQuery = "SELECT * FROM users WHERE email='$email'";
    $passresult = mysqli_query($conn, $checkEmailQuery);

    if (mysqli_num_rows($passresult) > 0) {
        $error_message .= "Error: Email already registered. Please use a different email.";
    }

    if ($pass !== $confirmpass) {
        $error_message .= "Error: Passwords do not match. Please enter matching passwords.";
    }

    if (empty($error_message)) {
        $signup_date = date('Y-m-d H:i:s');
        $query = "INSERT INTO users (firstname, lastname, contactnumber, email, password, signup_date) VALUES ('$firstname', '$lastname', '$number', '$email', '$password', '$signup_date')";

        if (mysqli_query($conn, $query)) {
            $_SESSION['user_id'] = "$firstname $lastname";
            $_SESSION['email'] = $email;
            $_SESSION['is_logged_in'] = isset($_SESSION['user_id']);

            $signup_successful = true;
        } else {
            echo "Error: " . $query . "<br>" . mysqli_error($conn);
        }
    }
}
?>

<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Sign Up</title>
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
            <?php if ($signup_successful): ?>
                alert("Signup successful!");
                window.location.href = "index.php"; 
                <?php elseif (!empty($error_message)): ?>
                alert("<?php echo addslashes(str_replace("\n", '\\n', $error_message)); ?>");
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
                    <li class="nav-item"><a class="nav-link" href="login.php">Log in</a></li>
                    <?php endif; ?>
                </ul>
            </div>
        </div>
    </nav>
    <section>
    <div class="registration">
        <h1>Sign Up</h1>
        <p>Already have an account? <a href="login.php">Log in</a> instead</p>

        <form id="signup" action="signup.php" method="POST">
            <table>
                <tr>
                    <td><label for="Fname"><h4>First Name:</h4></label></td>
                    <td><input type="text" name="firstname" id="Fname" required></td>
                </tr>
                <tr>
                    <td><label for="Lname"><h4>Last Name:</h4></label></td>
                    <td><input type="text" name="lastname" id="Lname" required></td>
                </tr>
                <tr>
                    <td><label for="number"><h4>Phone Number:</h4></label></td>
                    <td><input type="number" name="contactnumber" id="number" maxlength="11" title="Please enter exactly 11 digits." required></td>
                </tr>
                <tr>
                    <td><label for="email"><h4>Email Address:</h4></label></td>
                    <td><input type="email" name="email" id="email" required></td>
                </tr>
                <tr>
                    <td><label for="pass"><h4>Password:</h4></label></td>
                    <td><input type="password" name="password" id="pass" required></td>
                </tr>
                <tr>
                    <td><label for="pass2"><h4>Confirm Password:</h4></label></td>
                    <td><input type="password" name="confirmpassword" id="pass2" required></td>
                </tr>
            </table>
            
            <button type="submit" name="register" id="submit"><h3>Sign Up</h3></button>
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