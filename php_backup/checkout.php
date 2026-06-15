<?php
session_start();

require 'vendor/autoload.php';

use PHPMailer\PHPMailer\PHPMailer;
use PHPMailer\PHPMailer\Exception;

$conn = mysqli_connect("localhost", "root", "", "user_registration");

if (!$conn) {
    die("Connection failed: " . mysqli_connect_error());
}

if (!isset($_SESSION['user_id']) || !isset($_SESSION['email'])) {
    echo json_encode([
        'success' => false,
        'message' => 'User not logged in.'
    ]);
    exit();
}

$user_id = $_SESSION['user_id'];
$user_email = $_SESSION['email'];

session_regenerate_id(true);
$_SESSION['session_id'] = session_id();
$session_id = $_SESSION['session_id'];

/*
|--------------------------------------------------------------------------
| Build Receipt Before Clearing Cart
|--------------------------------------------------------------------------
*/

$cartQuery = "SELECT item_name, item_price FROM cart WHERE user_id = ?";
$cartStmt = $conn->prepare($cartQuery);
$cartStmt->bind_param("s", $user_id);
$cartStmt->execute();
$cartResult = $cartStmt->get_result();

$total = 0;

$receiptHTML = "
<h2>Dough Re Mi Patisserie</h2>

<p>Hello <strong>{$user_id}</strong>,</p>

<p>Thank you for your order! Here is your receipt.</p>

<table border='1' cellpadding='8' cellspacing='0' style='border-collapse:collapse;'>
<tr>
    <th>Item</th>
    <th>Price</th>
</tr>
";

while ($item = $cartResult->fetch_assoc()) {

    $receiptHTML .= "
    <tr>
        <td>{$item['item_name']}</td>
        <td>₱{$item['item_price']}</td>
    </tr>
    ";

    $total += $item['item_price'];
}

$receiptHTML .= "
<tr>
    <td><strong>Total</strong></td>
    <td><strong>₱{$total}</strong></td>
</tr>
</table>

<br>

<p><strong>Order Reference:</strong> {$session_id}</p>

<p>Thank you for shopping with Dough Re Mi Patisserie!</p>
";

/*
|--------------------------------------------------------------------------
| Move Cart Items To Orders
|--------------------------------------------------------------------------
*/

$query = "INSERT INTO orders (user_id, session_id, item_name, item_price)
          SELECT user_id, ?, item_name, item_price
          FROM cart
          WHERE user_id = ?";

$stmt = $conn->prepare($query);
$stmt->bind_param('ss', $session_id, $user_id);

if (!$stmt->execute()) {

    echo json_encode([
        'success' => false,
        'message' => 'Error moving items to orders: ' . $stmt->error
    ]);
    exit();
}

/*
|--------------------------------------------------------------------------
| Send Receipt Email
|--------------------------------------------------------------------------
*/

try {

    $mail = new PHPMailer(true);

    $mail->SMTPDebug = 2;
    $mail->Debugoutput = 'html';

    $mail->isSMTP();
    $mail->Host = 'smtp.gmail.com';
    $mail->SMTPAuth = true;

    $mail->Username = 'mjbbite@tip.edu.ph';
    $mail->Password = 'rfdoigkplrlgktos';

    $mail->SMTPSecure = PHPMailer::ENCRYPTION_STARTTLS;
    $mail->Port = 587;

    $mail->setFrom(
        'mjbbite@tip.edu.ph',
        'Dough Re Mi Patisserie'
    );

    $mail->addAddress(
        $user_email,
        $user_id
    );

    $mail->isHTML(true);
    $mail->Subject = "Receipt - Order #{$session_id}";
    $mail->Body = $receiptHTML;

    $mail->send();

} catch (Exception $e) {

    echo json_encode([
        'success' => false,
        'message' => $mail->ErrorInfo
    ]);

    exit();
}

/*
|--------------------------------------------------------------------------
| Clear Cart
|--------------------------------------------------------------------------
*/

$clearCartQuery = "DELETE FROM cart WHERE user_id = ?";

$clearStmt = $conn->prepare($clearCartQuery);
$clearStmt->bind_param('s', $user_id);

if (!$clearStmt->execute()) {

    echo json_encode([
        'success' => false,
        'message' => 'Error clearing cart: ' . $clearStmt->error
    ]);
    exit();
}

/*
|--------------------------------------------------------------------------
| Success Response
|--------------------------------------------------------------------------
*/

echo json_encode([
    'success' => true,
    'message' => 'Checkout completed successfully. Receipt sent to your email.'
]);

mysqli_close($conn);
?>