<?php
session_start();
$conn = mysqli_connect("localhost", "root", "", "user_registration");
if (!$conn) {
    die("Connection failed: " . mysqli_connect_error());
}

$user_id = $_SESSION['user_id'];
session_regenerate_id(true);
$_SESSION['session_id'] = session_id();
$session_id = $_SESSION['session_id'];

$query = "INSERT INTO orders (user_id, session_id, item_name, item_price)
          SELECT user_id, ?, item_name, item_price 
          FROM cart WHERE user_id = ?";
$stmt = $conn->prepare($query);
$stmt->bind_param('ss', $session_id, $user_id);

if (!$stmt->execute()) {
    echo json_encode(['success' => false, 'message' => 'Error moving items to orders: ' . $stmt->error]);
    exit();
}

$clearCartQuery = "DELETE FROM cart WHERE user_id = ?";
$clearStmt = $conn->prepare($clearCartQuery);
$clearStmt->bind_param('s', $user_id);

if (!$clearStmt->execute()) {
    echo json_encode(['success' => false, 'message' => 'Error clearing cart: ' . $clearStmt->error]);
    exit();
}

// Return success response
echo json_encode(['success' => true]);
?>