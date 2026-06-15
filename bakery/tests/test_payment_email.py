import unittest
from unittest.mock import patch
from bakery.email_service import send_payment_email
from bakery.order import Order

class TestPaymentEmail(unittest.TestCase):
    @patch('bakery.email_service.send_email')
    def test_email_sent_after_payment(self, mock_send_email):
        order = Order(amount=100, email='customer@example.com')
        order.complete_payment()
        send_payment_email(order)
        mock_send_email.assert_called_once_with('customer@example.com', 'Payment Confirmation', 'Thank you for your order!')

if __name__ == '__main__':
    unittest.main()