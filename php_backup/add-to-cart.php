<?php
session_start();
$conn = mysqli_connect("localhost", "root", "", "user_registration");

if (!$conn) {
    die("Connection failed: " . mysqli_connect_error());
}

if (!isset($_SESSION['user_id'])) {
    echo json_encode(['message' => 'User  not logged in']);
    exit();
}

$data = json_decode(file_get_contents("php://input"), true);

if (isset($data['name']) && isset($data['price'])) {

    $user_id = $_SESSION['user_id']; 
    $item_name = $data['name'];
    $item_price = $data['price'];

    $query = "INSERT INTO cart (user_id, item_name, item_price) VALUES (?, ?, ?)";
    $stmt = $conn->prepare($query);
    $stmt->bind_param('ssd', $user_id, $item_name, $item_price); // 'isd' - integer, string, decimal

    if ($stmt->execute()) {
        echo json_encode(['message' => 'Item added to cart']);
    } else {
        echo json_encode(['message' => 'Error adding item to cart: ' . $stmt->error]);
    }
    
} else {
    echo json_encode(['message' => 'Item data missing']);
}
?>