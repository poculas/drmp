from django.test import TestCase, Client
from django.urls import reverse
from django.core.cache import cache
from django.contrib.auth.models import User
from bakery.utils import generate_captcha_svg
from bakery.models import Product

class SecurityTestCase(TestCase):
    def setUp(self):
        self.client = Client()
        cache.clear()
        
    def test_generate_captcha_svg(self):
        # Test that the captcha utility generates a non-empty SVG string
        svg = generate_captcha_svg("A1B2C")
        self.assertTrue(svg.startswith('<svg'))
        self.assertTrue(svg.endswith('</svg>'))
        self.assertIn("A", svg)
        self.assertIn("1", svg)
        
    def test_captcha_view(self):
        # Test captcha view returns SVG and sets code in session
        response = self.client.get(reverse('captcha_image'))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response['Content-Type'], 'image/svg+xml')
        self.assertIn('captcha_code', self.client.session)
        self.assertEqual(len(self.client.session['captcha_code']), 5)
        
    def test_login_captcha_validation_failure(self):
        # Generate captcha session first
        self.client.get(reverse('captcha_image'))
        
        # Post bad captcha
        response = self.client.post(reverse('login'), {
            'email': 'test@example.com',
            'password': 'Password123!',
            'captcha': 'WRONG'
        })
        self.assertEqual(response.status_code, 200)
        # Verify the session captcha is cleared and error message is returned
        self.assertNotIn('captcha_code', self.client.session)
        messages = list(response.context.get('messages') or [])
        self.assertTrue(any("Invalid CAPTCHA" in str(m) for m in messages))
        
    def test_login_captcha_validation_success_bad_credentials(self):
        # Generate captcha session first
        self.client.get(reverse('captcha_image'))
        code = self.client.session['captcha_code']
        
        # Post correct captcha but bad email
        response = self.client.post(reverse('login'), {
            'email': 'wrong@example.com',
            'password': 'Password123!',
            'captcha': code
        })
        self.assertEqual(response.status_code, 200)
        messages = list(response.context.get('messages') or [])
        # Captcha passed, but authentication failed
        self.assertTrue(any("Incorrect Username or Password!" in str(m) for m in messages))
        self.assertFalse(any("Invalid CAPTCHA" in str(m) for m in messages))

    def test_signup_captcha_validation_failure(self):
        # Generate captcha session first
        self.client.get(reverse('captcha_image'))
        
        # Post bad captcha to signup
        response = self.client.post(reverse('signup'), {
            'first_name': 'Test',
            'last_name': 'User',
            'contactnumber': '09123456789',
            'email': 'newuser@example.com',
            'password': 'Password123!',
            'confirm_password': 'Password123!',
            'captcha': 'WRONG'
        })
        self.assertEqual(response.status_code, 200)
        # Check that error is returned
        messages = list(response.context.get('messages') or [])
        self.assertTrue(any("Invalid CAPTCHA" in str(m) for m in messages))

    def test_signup_rate_limiting(self):
        # Hit signup endpoint 6 times with POST requests
        for i in range(6):
            self.client.post(reverse('signup'), {
                'first_name': 'Test',
                'last_name': 'User',
                'contactnumber': '09123456789',
                'email': f'newuser{i}@example.com',
                'password': 'Password123!',
                'confirm_password': 'Password123!',
                'captcha': 'WRONG'
            })
            
        # The 6th post (or subsequent) should fail with rate limit error
        # Note: 127.0.0.1 is client IP by default in Client requests
        response = self.client.post(reverse('signup'), {
            'first_name': 'Test',
            'last_name': 'User',
            'contactnumber': '09123456789',
            'email': 'newuser6@example.com',
            'password': 'Password123!',
            'confirm_password': 'Password123!',
            'captcha': 'WRONG'
        })
        
        self.assertEqual(response.status_code, 200)
        messages = list(response.context.get('messages') or [])
        self.assertTrue(any("Too many signup attempts" in str(m) for m in messages))

class CartTestCase(TestCase):
    def setUp(self):
        self.client = Client()
        self.user = User.objects.create_user(username='customer@example.com', email='customer@example.com', password='Password123!')
        self.product = Product.objects.create(name='Test Croissant', price=50.00, stock=10)
        
    def test_unauthenticated_add_to_cart_redirects(self):
        # Post to cart_add while unauthenticated
        response = self.client.post(reverse('cart_add'), {
            'name': 'Test Croissant',
            'quantity': 2
        }, content_type='application/json')
        # Django's login_required decorator redirects unauthenticated requests (HTTP 302)
        self.assertEqual(response.status_code, 302)
        self.assertTrue(response.url.startswith('/login.php'))
        
    def test_authenticated_add_custom_quantity(self):
        # Log in first
        self.client.login(username='customer@example.com', password='Password123!')
        
        # Post to cart_add
        response = self.client.post(reverse('cart_add'), {
            'name': 'Test Croissant',
            'quantity': 3
        }, content_type='application/json')
        
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data['message'], 'Item added to cart')
        
        # Verify cart item quantity is 3
        from bakery.models import CartItem
        cart_item = CartItem.objects.get(user=self.user, product=self.product)
        self.assertEqual(cart_item.quantity, 3)

        self.client.post(reverse('cart_add'), {
            'name': 'Test Croissant',
            'quantity': 2
        }, content_type='application/json')
        cart_item.refresh_from_db()
        self.assertEqual(cart_item.quantity, 5)

    def test_checkout_empty_cart(self):
        self.client.login(username='customer@example.com', password='Password123!')
        response = self.client.post(reverse('checkout'))
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertFalse(data['success'])
        self.assertEqual(data['message'], 'You need to add an item first!')

    def test_checkout_with_items(self):
        self.client.login(username='customer@example.com', password='Password123!')
        # Add item to cart first
        self.client.post(reverse('cart_add'), {
            'name': 'Test Croissant',
            'quantity': 2
        }, content_type='application/json')
        
        response = self.client.post(reverse('checkout'))
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertTrue(data['success'])
        
        # Verify order was created
        from bakery.models import Order, CartItem
        orders = Order.objects.filter(user=self.user)
        self.assertEqual(orders.count(), 2) # quantity was 2, so 2 orders created
        self.assertEqual(orders[0].item_name, 'Test Croissant')
        
        # Verify cart was cleared
        self.assertFalse(CartItem.objects.filter(user=self.user).exists())

