<?php
session_start();

if(!isset($_SESSION['is_logged_in'])){
    $_SESSION['is_logged_in'] = false;
}
?>

<!DOCTYPE html>
<html lang="en">
  <head>
    <meta charset="UTF-8" />
    <meta name="viewport" content="width=device-width, initial-scale=1.0" />
    <title>Je'Cole's Bakery - Home</title>
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
<style>
   .hero-section video {
    position: absolute;
    top: 50%;
    left: 50%;
    width: 100%;
    height: 100%;
    object-fit: cover;
    transform: translate(-50%, -50%);
    z-index: -1;
  }
.hero-section::before {
    content: "";
    position: absolute;
    top: 0;
    left: 0;
    width: 100%;
    height: 100%;
    background: linear-gradient(
      to bottom right,
      rgba(0, 0, 0, 0.6),
      rgba(0, 0, 0, 0.2)
    );
    z-index: 0;
  }

  .hero-content {
    position: absolute;
    top: 50%;
    left: 50%;
    transform: translate(-50%, -50%);
    color: white;
    text-align: center;
    z-index: 1;
  }

  .btn-custom {
    background-color: #ff5a5f;
    color: white;
    padding: 10px 20px;
    border-radius: 5px;
    text-decoration: none;
  }

  .btn-custom:hover {
    background-color: #ff8a80;
  }
  .hero-content h1 {
    font-size: 3.5rem;
    font-weight: 700;
    margin-bottom: 1rem;
  }
  .hero-content p {
    font-size: 1.5rem;
    margin-bottom: 2rem;
  }
  .btn-custom {
    background-color: #e74c3c;
    color: white;
    border: none;
    padding: 10px 30px;
    font-weight: 600;
    text-transform: uppercase;
    letter-spacing: 1px;
    transition: all 0.3s ease;
  }
  .btn-custom:hover {
    background-color: #c0392b;
    transform: translateY(-3px);
  }
  .section-title {
    font-size: 2.5rem;
    font-weight: 700;
    text-align: center;
    margin-bottom: 3rem;
    color: #8b4513;
  }
  .featured-product {
    background-color: white;
    border-radius: 10px;
    overflow: hidden;
    box-shadow: 0 4px 15px rgba(0, 0, 0, 0.1);
    transition: all 0.3s ease;
  }
  .featured-product:hover {
    transform: translateY(-10px);
  }
  .featured-product img {
    width: 100%;
    height: 250px;
    object-fit: cover;
  }
  .featured-product-content {
    padding: 1.5rem;
  }
  .about-section,
  .why-choose-us,
  .our-process,
  .gallery-section {
    background-color: white;
    border-radius: 10px;
    padding: 3rem;
    box-shadow: 0 4px 15px rgba(0, 0, 0, 0.1);
    margin-bottom: 3rem;
  }
  .testimonial {
    background-color: white;
    border-radius: 10px;
    padding: 2rem;
    box-shadow: 0 4px 15px rgba(0, 0, 0, 0.1);
    margin-bottom: 2rem;
  }
  .testimonial-image {
    width: 80px;
    height: 80px;
    border-radius: 50%;
    object-fit: cover;
    margin-bottom: 1rem;
  }
  .testimonial-rating {
    color: #f1c40f;
    font-size: 1.2rem;
    margin-bottom: 0.5rem;
  }
  .process-step {
    text-align: center;
    padding: 1rem;
  }
  .process-step i {
    font-size: 3rem;
    color: #e74c3c;
    margin-bottom: 1rem;
  }
  .gallery-image {
    width: 100%;
    height: 200px;
    object-fit: cover;
    border-radius: 10px;
    margin-bottom: 1rem;
  }
  
  .testimonial h6 {
    font-size: 16px;
    font-weight: bold;
    color: #333;
    margin-top: 10px;
    position: relative;
    display: inline-block;
    padding-left: 20px;
  }

  .testimonial h6::before {
    content: "";
    position: absolute;
    left: 0;
    top: 50%;
    transform: translateY(-50%);
    height: 2px;
    width: 15px;
    background-color: #ff5a5f;
  }

  .testimonial h6 span {
    font-style: normal;
    color: #999;
    font-weight: 400;
  }
</style>
  </head>
  <body>
    <nav class="navbar navbar-expand-lg navbar-dark">
        <div class="container">
            <a class="navbar-brand" href="index.php"><img src="images/logoWhite.png" alt="Je'Cole's Bakery"></a>
            <button class="navbar-toggler" type="button" data-bs-toggle="collapse" data-bs-target="#navbarNav" aria-controls="navbarNav" aria-expanded="false" aria-label="Toggle navigation">
                <span class="navbar-toggler-icon"></span>
            </button>
            <div class="collapse navbar-collapse" id="navbarNav">
                <ul class="navbar-nav ms-auto">
                    <li class="nav-item"><a class="nav-link active" href="index.php">Home</a></li>
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

    <header class="hero-section">
      <video autoplay loop muted playsinline>
        <source src="media/paris.mp4" type="video/mp4" />
      </video>
      <div class="hero-content">
        <h1>Welcome to Je'Cole's Bakery</h1>
        <p>Experience the taste of freshly baked French pastries</p>
        <a
          href="menu.php"
          class="btn btn-custom btn-lg"
          aria-label="View Our Menu"
          >View Our Menu</a
        >
      </div>
    </header>

    <main class="container my-5">
      <section class="featured-products">
        <h2 class="section-title">Featured Products</h2>
        <div class="row g-4">
          <div class="col-md-4">
            <div class="featured-product">
              <img src="images/croissant.png" alt="Classic Croissant" />
              <div class="featured-product-content">
                <h3>Classic Croissant</h3>
                <p>Buttery, flaky, and perfectly golden.</p>
              </div>
            </div>
          </div>
          <div class="col-md-4">
            <div class="featured-product">
              <img src="images/baguette.png" alt="Medium Baguette" />
              <div class="featured-product-content">
                <h3>Medium Baguette</h3>
                <p>Crispy crust with a soft, airy interior.</p>
              </div>
            </div>
          </div>
          <div class="col-md-4">
            <div class="featured-product">
              <img src="images/Pan au Chocolat.png" alt="Pan au Chocolat" />
              <div class="featured-product-content">
                <h3>Pan au Chocolat</h3>
                <p>Flaky pastry filled with rich chocolate.</p>
              </div>
            </div>
          </div>
        </div>
      </section>

      <section class="about-us my-5">
        <div class="about-section">
          <div class="row align-items-center">
            <div class="col-md-6">
              <h2 class="section-title text-start">About Je'Cole's Bakery</h2>
              <p>
                At Je'Cole's Bakery, we're passionate about creating authentic
                French pastries using traditional techniques and the finest
                ingredients. Our master bakers bring a taste of Paris to your
                neighborhood, ensuring each bite is a delightful experience.
              </p>
              <p>
                Founded in 2010, Je'Cole's Bakery has become a beloved
                institution in our community, known for our commitment to
                quality and our warm, welcoming atmosphere.
              </p>
              <a href="aboutus.php" class="btn btn-custom mt-3">Learn More</a>
            </div>
            <div class="col-md-6">
              <img
                src="https://images.unsplash.com/photo-1635907487589-4b8b2a63f704?q=80&w=2159&auto=format&fit=crop&ixlib=rb-4.0.3&ixid=M3wxMjA3fDB8MHxwaG90by1wYWdlfHx8fGVufDB8fHx8fA%3D%3D"
                alt="Baker at work"
                class="img-fluid rounded"
              />
            </div>
          </div>
        </div>
      </section>

      <section class="why-choose-us my-5">
        <h2 class="section-title">Why Choose Je'Cole's Bakery?</h2>
        <div class="row">
          <div class="col-md-4 mb-4">
            <div class="text-center">
              <i
                class="fas fa-solid fa-map-pin fa-3x mb-3"
                style="color: #e74c3c"
              ></i>
              <h3>Premium Ingredients</h3>
              <p>
                We use only the finest, locally-sourced ingredients to ensure
                the best quality in every bite.
              </p>
            </div>
          </div>
          <div class="col-md-4 mb-4">
            <div class="text-center">
              <i class="fas fa-hands fa-3x mb-3" style="color: #e74c3c"></i>
              <h3>Handcrafted with Love</h3>
              <p>
                Each pastry is carefully handcrafted by our skilled bakers with
                attention to detail and passion.
              </p>
            </div>
          </div>
          <div class="col-md-4 mb-4">
            <div class="text-center">
              <i class="fas fa-clock fa-3x mb-3" style="color: #e74c3c"></i>
              <h3>Fresh Daily</h3>
              <p>
                We bake our products fresh every day to ensure you always get
                the best quality and taste.
              </p>
            </div>
          </div>
        </div>
      </section>

      <section class="our-process my-5">
        <h2 class="section-title">Our Baking Process</h2>
        <div class="row">
          <div class="col-md-3">
            <div class="process-step">
              <i class="fas fa-shopping-basket"></i>
              <h4>1. Ingredient Selection</h4>
              <p>We carefully select the finest ingredients for our recipes.</p>
            </div>
          </div>
          <div class="col-md-3">
            <div class="process-step">
              <i class="fas fa-mortar-pestle"></i>
              <h4>2. Preparation</h4>
              <p>Our bakers prepare the dough with precision and care.</p>
            </div>
          </div>
          <div class="col-md-3">
            <div class="process-step">
              <i class="fas fa-temperature-high"></i>
              <h4>3. Baking</h4>
              <p>
                We bake our pastries to perfection in state-of-the-art ovens.
              </p>
            </div>
          </div>
          <div class="col-md-3">
            <div class="process-step">
              <i class="fas fa-smile-beam"></i>
              <h4>4. Serving</h4>
              <p>We serve our freshly baked goods with a warm smile.</p>
            </div>
          </div>
        </div>
      </section>

      <section class="gallery-section my-5">
        <h2 class="section-title">Our Bakery Gallery</h2>
        <div class="row">
          <div class="col-md-4 mb-4">
            <img
              src="images/Strawberry Macaroons.png"
              class="gallery-image"
            />
          </div>
          <div class="col-md-4 mb-4">
            <img
              src="images/Paris-Brest.png"
              class="gallery-image"
            />
          </div>
          <div class="col-md-4 mb-4">
            <img
              src="images/Pan au Chocolat.png"
              class="gallery-image"
            />
          </div>
          <div class="col-md-4 mb-4">
            <img
              src="images/Eclair.png"
              class="gallery-image"
            />
          </div>
          <div class="col-md-4 mb-4">
            <img
              src="images/croissant.png"
              class="gallery-image"
            />
          </div>
          <div class="col-md-4 mb-4">
            <img
              src="images/baguette.png"
              class="gallery-image"
            />
          </div>
        </div>
      </section>

      <section class="testimonials my-5">
        <h2 class="section-title">What Our Customers Say</h2>
        <div class="row">
          <div class="col-md-6 mb-4">
            <div class="testimonial">
              <img
                src="images/jay.jpg"
                class="testimonial-image"
              />
              <div class="testimonial-rating">
                <i class="fas fa-star"></i>
                <i class="fas fa-star"></i>
                <i class="fas fa-star"></i>
                <i class="fas fa-star"></i>
                <i class="fas fa-star"></i>
              </div>
              <p>
                "The croissants at Je'Cole's are simply divine. They transport
                me back to the streets of Paris with every bite! The buttery
                layers and perfect flakiness are unmatched. I've tried
                croissants all over the city, but none compare to these."
              </p>
              <h6>Josephine Kagat</h6>
            </div>
          </div>
          <div class="col-md-6 mb-4">
            <div class="testimonial">
              <img
                src="images/izel.jpg"
                class="testimonial-image"
              />
              <div class="testimonial-rating">
                <i class="fas fa-star"></i>
                <i class="fas fa-star"></i>
                <i class="fas fa-star"></i>
                <i class="fas fa-star"></i>
                <i class="fas fa-star-half-alt"></i>
              </div>
              <p>
                "I've never tasted a baguette this good outside of France.
                Je'Cole's has nailed the perfect crust-to-crumb ratio! The crust
                is crispy and the inside is soft and airy. It's become a staple
                in our household for family dinners."
              </p>
              <h6>Gcell Batumbakal</h6>
            </div>
          </div>
          <div class="col-md-6 mb-4">
            <div class="testimonial">
              <img
                src="images/ng, nikolai.jpg"
                class="testimonial-image"
              />
              <div class="testimonial-rating">
                <i class="fas fa-star"></i>
                <i class="fas fa-star"></i>
                <i class="fas fa-star"></i>
                <i class="fas fa-star"></i>
                <i class="fas fa-star"></i>
              </div>
              <p>
                "As a professional chef, I have high standards for pastries.
                Je'Cole's Bakery exceeds them all. Their attention to detail and
                commitment to using high-quality ingredients is evident in every
                bite. The Pain au Chocolat is particularly outstanding."
              </p>
              <h6>Nicholas Matigas</h6>
            </div>
          </div>
          <div class="col-md-6 mb-4">
            <div class="testimonial">
              <img
                src="images/me.jpg"
                class="testimonial-image"
              />
              <div class="testimonial-rating">
                <i class="fas fa-star"></i>
                <i class="fas fa-star"></i>
                <i class="fas fa-star"></i>
                <i class="fas fa-star"></i>
                <i class="far fa-star"></i>
              </div>
              <p>
                "Je'Cole's Bakery has become my go-to place for client meetings.
                The atmosphere is perfect, and the pastries always impress.
                Their selection of French pastries adds a touch of
                sophistication to our discussions. Highly recommended for
                business or pleasure!"
              </p>
              <h6>Jeremiah Cupal</h6>
            </div>
          </div>
        </div>
      </section>

      <section class="cta-section my-5 text-center">
        <h2 class="section-title">Ready to Taste the Difference?</h2>
        <p class="lead mb-4">
          Visit Je'Cole's Bakery today and experience the magic of authentic
          French pastries!
        </p>
        <a href="menu.php" class="btn btn-custom btn-lg">Order Now</a>
      </section>
    </main>

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
                    <p>© 2024, Je'Cole's Bakery Online Quiapo Manila</p>
                    <p>Je'Cole's Bakery Online</p>
                </div>
            </div>
        </div>
    </footer>
    </footer>


    <script src="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0-alpha1/dist/js/bootstrap.bundle.min.js"></script>
  </body>
</html>
