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

import os
import logging
from django.conf import settings
from bakery.models import AuditLog

class LoggingTestCase(TestCase):
    def setUp(self):
        self.log_dir = os.path.join(settings.BASE_DIR, 'logs')
        self.security_log_path = os.path.join(self.log_dir, 'security.log')
        self.error_log_path = os.path.join(self.log_dir, 'errors.log')
        
    def test_log_directory_and_files_exist(self):
        # Verify that the logs directory is created
        self.assertTrue(os.path.isdir(self.log_dir))
        
        # Write dummy warning/info log to populate the files
        logger = logging.getLogger('security')
        logger.info("TEST_LOG_MESSAGE_SECURITY")
        
        err_logger = logging.getLogger('django.request')
        err_logger.error("TEST_LOG_MESSAGE_ERROR")
        
        # Verify files exist and are populated
        self.assertTrue(os.path.isfile(self.security_log_path))
        self.assertTrue(os.path.isfile(self.error_log_path))
        
        with open(self.security_log_path, 'r') as f:
            content = f.read()
            self.assertIn("TEST_LOG_MESSAGE_SECURITY", content)
            
        with open(self.error_log_path, 'r') as f:
            content = f.read()
            self.assertIn("TEST_LOG_MESSAGE_ERROR", content)

    def test_decoupled_audit_logging(self):
        # Clear existing file contents to avoid collision
        if os.path.isfile(self.security_log_path):
            with open(self.security_log_path, 'w') as f:
                f.write('')
                
        user = User.objects.create_user(username='staff@example.com', email='staff@example.com', password='Password123!')
        
        # Create database AuditLog record
        AuditLog.objects.create(
            user=user,
            action='product_create',
            description="Created a test product",
            ip_address="127.0.0.1"
        )
        
        # Verify that save() override correctly wrote to security.log
        self.assertTrue(os.path.isfile(self.security_log_path))
        with open(self.security_log_path, 'r') as f:
            content = f.read()
            self.assertIn("AUDIT_LOG", content)
            self.assertIn("product_create", content)
            self.assertIn("Created a test product", content)
            self.assertIn("staff@example.com", content)

from bakery.forms import DeliveryForm
from bakery.models import MFACode
from django.utils import timezone
from datetime import timedelta

class InputValidationTestCase(TestCase):
    def setUp(self):
        self.client = Client()
        self.user = User.objects.create_user(username='cust@example.com', email='cust@example.com', password='Password123!')
        self.product = Product.objects.create(name='Valid Croissant', price=40.00, stock=10)

    def test_delivery_form_validation(self):
        # Test valid data
        form_data = {
            'houseNumber': 12,
            'street': 'Main St',
            'barangay': 'San Jose',
            'city': 'Manila',
            'postalCode': 1000,
            'paymentMethod': 'Gcash'
        }
        form = DeliveryForm(data=form_data)
        self.assertTrue(form.is_valid())

        # Test invalid houseNumber (0 and negative)
        form_data['houseNumber'] = 0
        form = DeliveryForm(data=form_data)
        self.assertFalse(form.is_valid())
        self.assertIn('houseNumber', form.errors)

        form_data['houseNumber'] = -5
        form = DeliveryForm(data=form_data)
        self.assertFalse(form.is_valid())
        self.assertIn('houseNumber', form.errors)

        # Test invalid postalCode (0 and negative)
        form_data['houseNumber'] = 12
        form_data['postalCode'] = 0
        form = DeliveryForm(data=form_data)
        self.assertFalse(form.is_valid())
        self.assertIn('postalCode', form.errors)

        form_data['postalCode'] = -100
        form = DeliveryForm(data=form_data)
        self.assertFalse(form.is_valid())
        self.assertIn('postalCode', form.errors)

    def test_cart_add_negative_or_zero_quantity(self):
        self.client.login(username='cust@example.com', password='Password123!')
        
        # Try adding zero quantity
        response = self.client.post(reverse('cart_add'), {
            'name': 'Valid Croissant',
            'quantity': 0
        }, content_type='application/json')
        self.assertEqual(response.status_code, 400)
        self.assertIn('Quantity must be greater than zero', response.json()['message'])

        # Try adding negative quantity
        response = self.client.post(reverse('cart_add'), {
            'name': 'Valid Croissant',
            'quantity': -5
        }, content_type='application/json')
        self.assertEqual(response.status_code, 400)
        self.assertIn('Quantity must be greater than zero', response.json()['message'])


class MFABruteForceTestCase(TestCase):
    def setUp(self):
        self.client = Client()
        cache.clear()
        self.user = User.objects.create_user(username='mfauser@example.com', email='mfauser@example.com', password='Password123!')
        self.mfa_code = MFACode.objects.create(
            user=self.user,
            code='123456',
            method='email',
            expires_at=timezone.now() + timedelta(minutes=10)
        )
        
    def test_mfa_brute_force_lockout(self):
        # Set session variable to simulate multi-factor authentication flow
        session = self.client.session
        session['mfa_user_id'] = self.user.id
        session['mfa_method'] = 'email'
        session.save()
        
        # First 4 attempts with wrong codes should fail but keep user in MFA flow
        for i in range(4):
            response = self.client.post(reverse('verify_mfa'), {'code': 'wrong'})
            self.assertEqual(response.status_code, 200) # still on page
            self.assertIn('mfa_user_id', self.client.session)
            
        # The 5th incorrect attempt should delete the code and lock the session
        response = self.client.post(reverse('verify_mfa'), {'code': 'wrong'})
        self.assertEqual(response.status_code, 302) # redirects to login
        self.assertNotIn('mfa_user_id', self.client.session)
        self.assertFalse(MFACode.objects.filter(user=self.user).exists())



