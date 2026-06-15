from unittest import TestCase
from unittest.mock import patch

class TestPaymentEmail(TestCase):
    @patch('bakery.email.send_email')
    def test_email_sent_on_successful_payment(self, mock_send_email):
        # Simulate a successful payment
        order = {'id': 1, 'amount': 100}
        # Call the function that processes the payment
        process_payment(order)
        
        # Assert that the email sending function was called
        mock_send_email.assert_called_once_with(order['id'])