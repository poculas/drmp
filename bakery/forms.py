import re
from django import forms
from django.contrib.auth.models import User
from django.core.exceptions import ValidationError

class SignUpForm(forms.ModelForm):
    first_name = forms.CharField(max_length=50, required=True, label="First Name")
    last_name = forms.CharField(max_length=50, required=True, label="Last Name")
    contactnumber = forms.CharField(max_length=11, required=True, label="Phone Number")
    email = forms.EmailField(required=True, label="Email Address")
    password = forms.CharField(widget=forms.PasswordInput(), required=True, label="Password")
    confirm_password = forms.CharField(widget=forms.PasswordInput(), required=True, label="Confirm Password")

    class Meta:
        model = User
        fields = ['first_name', 'last_name', 'email']

    def clean_contactnumber(self):
        contactnumber = self.cleaned_data.get('contactnumber')
        if not re.match(r'^\d{11}$', contactnumber):
            raise ValidationError("Phone number must be exactly 11 digits.")
        from bakery.models import UserProfile
        if UserProfile.objects.filter(contactnumber=contactnumber).exists():
            raise ValidationError("Phone number is already registered.")
        return contactnumber

    def clean_email(self):
        email = self.cleaned_data.get('email')
        if User.objects.filter(email=email).exists():
            raise ValidationError("Email is already registered.")
        return email

    def clean(self):
        cleaned_data = super().clean()
        password = cleaned_data.get("password")
        confirm_password = cleaned_data.get("confirm_password")

        if password and confirm_password and password != confirm_password:
            self.add_error('confirm_password', "Passwords do not match. Please enter matching passwords.")
        return cleaned_data

class DeliveryForm(forms.Form):
    PAYMENT_CHOICES = [
        ('', 'Select a payment method'),
        ('Gcash', 'Gcash'),
        ('PayMaya', 'PayMaya'),
        ('BDO', 'BDO'),
        ('Cash on delivery', 'Cash on delivery'),
    ]

    houseNumber = forms.IntegerField(required=True, label="House/Unit No.")
    street = forms.CharField(max_length=55, required=True, label="Street")
    barangay = forms.CharField(max_length=55, required=True, label="Barangay")
    city = forms.CharField(max_length=55, required=True, label="City")
    postalCode = forms.IntegerField(required=True, label="Postal Code")
    paymentMethod = forms.ChoiceField(choices=PAYMENT_CHOICES, required=True, label="Payment Method")
