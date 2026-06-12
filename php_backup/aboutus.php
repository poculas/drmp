<?php
session_start();

if (!isset($_SESSION['is_logged_in'])) {
    $_SESSION['is_logged_in'] = false;
}
?>

<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Dough Re Mi Patisserie</title>
    <link rel="stylesheet" href="aboutus.css">
    <link rel="icon" href="images/tab.png">
    <link rel="stylesheet" href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0-alpha1/dist/css/bootstrap.min.css">
    <link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.0.0-beta3/css/all.min.css">
    <link rel ="stylesheet" href="styles.css">
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
                    <li class="nav-item"><a class="nav-link active" href="aboutus.php">About Us</a></li>
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
    <video autoplay loop muted plays-inline>
        <source src="media/bread.mp4" type="video/mp4">
    </video>
    <div class="slider">
        <div class="list">
            <div class="item">
                <div class="content">
                    <div class="title">Dough Re Mi</div>
                    <div class="type">Patisserie</div>
                    <div class="description">
                        Welcome to our online bakery! a convenient platform where fresh, delicious breada
                        is just a few clicks away! Our project aims to make it easier for customers to enjoy high-quality,
                        artisan bread without leaving the comfort of their homes. With a wide variety of bread options to
                        choose from, our website allows users to browse, order, and have their favorite loaves delivered
                        right to their doorstep. Founded in 2024, Dough Re Mi Patisserie began with a vision to bring the authentic 
                        flavors of French pastry to Manila, Philippines. Drawing inspiration from the rich baking traditions 
                        of France, the bakery was established to introduce Filipinos to exquisite breads, pastries, and desserts. 
                        With a focus on quality ingredients and traditional techniques, Dough Re Mi Patisserie quickly gained a reputation 
                        for offering a taste of France in the heart of Manila, becoming a destination for those seeking artisanal 
                        baked goods with a French flair.
                    </div>
                </div>
            </div>
            <div class="item">
                <div class="content">
                    <div class="title">About our</div>
                    <div class="type">Breads</div>
                        <div class="description">
                            Dough Re Mi Patisserie, brings the timeless elegance of French baking to your table.a
                            Specializing in classic French breads, we offer a selection that showcases the rich, flavorful
                            tradition of French cuisine. From the perfect baguette to artisanal loaves, each bread is crafted
                            with passion and precision to bring you an authentic taste of France in every bite. 
                            Dough Re Mi French pastries offers a sensory experience that begins with their delicate, golden-brown
                            crusts and ends with rich, flavorful fillings. Each bite is a symphony of textures—light and flaky 
                            layers that melt in your mouth, often giving way to smooth creams or rich chocolate centers. The buttery, 
                            slightly sweet aroma entices the senses, while the balanced flavors of almond, vanilla, or fruit add a
                            touch of sophistication. Whether you're enjoying a croissant, éclair, or tart, these pastries deliver a 
                            perfect blend of crispiness and softness, making every bite a luxurious treat. At Dough Re Mi Patisserie, we
                            believe that every loaf tells a story, and we are excited to share ours with you.
                       </div>                  
                    </div>
                </div>
                    <div class="thumbnail">
                        <div class="item">
                            <img src="images/roch.jpg"alt="">
                        </div>
                        <div class="item">
                            <img src="images/logo.jpg" alt="">
                        </div>
                        <div class="item">
                            <img src="images/CA.jpg"alt="">
                        </div>
                        <div class="item">
                            <img src="images/me.jpg"alt="">
                        </div>
                        <div class="item">
                            <img src="images/jay.jpg"alt="">
                        </div>
                        <div class="item">
                            <img src="images/ng.jpg"alt="">
                        </div>
                        <div class="item">
                            <img src="images/jizel.jpg"alt="">
                        </div>
                    </div>
                    <div class="nextPrevArrows">
                        <button class="prev"> < </button>
                        <button class="next"> > </button>
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

    <script src="scripts/aboutus.js"></script>
    <script src="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0-alpha1/dist/js/bootstrap.bundle.min.js"></script>
</body>
</html>


