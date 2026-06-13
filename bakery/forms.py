import re
from django import forms
from django.contrib.auth.models import User
from django.core.exceptions import ValidationError

from bakery.models import UserProfile, Product, Order

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

    def clean_houseNumber(self):
        house_number = self.cleaned_data.get('houseNumber')
        if house_number is not None and house_number <= 0:
            raise ValidationError("House number must be a positive integer.")
        return house_number

    def clean_postalCode(self):
        postal_code = self.cleaned_data.get('postalCode')
        if postal_code is not None and postal_code <= 0:
            raise ValidationError("Postal code must be a positive integer.")
        return postal_code

class StaffCreateForm(forms.ModelForm):
    email = forms.EmailField(required=True, label="Email Address")
    password = forms.CharField(widget=forms.PasswordInput(), required=True, label="Password")
    
    class Meta:
        model = User
        fields = ['email']
    
    def clean_email(self):
        email = self.cleaned_data.get('email')
        if User.objects.filter(email=email).exists():
            raise ValidationError("Email is already registered.")
        return email
    
    def save(self, commit=True):
        user = super().save(commit=False)
        user.set_password(self.cleaned_data['password'])
        user.username = self.cleaned_data['email']
        if commit:
            user.save()
            # Create UserProfile with staff role
            UserProfile.objects.create(
                user=user,
                role='staff',
                is_active=True
            )
        return user

class StaffEditForm(forms.ModelForm):
    first_name = forms.CharField(max_length=50, required=True, label="First Name")
    last_name = forms.CharField(max_length=50, required=True, label="Last Name")
    email = forms.EmailField(required=True, label="Email Address")
    contactnumber = forms.CharField(max_length=11, required=True, label="Phone Number")
    is_active = forms.BooleanField(required=False, label="Active")
    
    class Meta:
        model = User
        fields = ['first_name', 'last_name', 'email']
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if self.instance and hasattr(self.instance, 'profile'):
            self.fields['contactnumber'].initial = self.instance.profile.contactnumber
            self.fields['is_active'].initial = self.instance.profile.is_active
    
    def clean_contactnumber(self):
        contactnumber = self.cleaned_data.get('contactnumber')
        if not re.match(r'^\d{11}$', contactnumber):
            raise ValidationError("Phone number must be exactly 11 digits.")
        # Check if phone number is already registered by another user
        if UserProfile.objects.filter(contactnumber=contactnumber).exclude(user=self.instance).exists():
            raise ValidationError("Phone number is already registered.")
        return contactnumber
    
    def clean_email(self):
        email = self.cleaned_data.get('email')
        # Check if email is already registered by another user
        if User.objects.filter(email=email).exclude(id=self.instance.id).exists():
            raise ValidationError("Email is already registered.")
        return email
    
    def save(self, commit=True):
        user = super().save(commit=False)
        if commit:
            user.save()
            # Update UserProfile
            profile = user.profile
            profile.contactnumber = self.cleaned_data['contactnumber']
            profile.is_active = self.cleaned_data['is_active']
            profile.save()
        return user

class ProductForm(forms.ModelForm):
    class Meta:
        model = Product
        fields = ['name', 'price', 'image', 'description', 'stock', 'is_available']
        widgets = {
            'name': forms.TextInput(attrs={'class': 'form-control'}),
            'price': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01'}),
            'image': forms.FileInput(attrs={'class': 'form-control', 'accept': 'image/*'}),
            'description': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
            'stock': forms.NumberInput(attrs={'class': 'form-control'}),
            'is_available': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        }
    
    def clean_image(self):
        image = self.cleaned_data.get('image')
        if image:
            # Check if it's an uploaded file (not a string from existing image)
            if hasattr(image, 'size'):
                # Check file size (3MB = 3 * 1024 * 1024 bytes)
                if image.size > 3 * 1024 * 1024:
                    raise ValidationError("Image file size must be no more than 3MB.")
        return image

class OrderStatusForm(forms.ModelForm):
    class Meta:
        model = Order
        fields = ['status']
        widgets = {
            'status': forms.Select(attrs={'class': 'form-control'}),
        }


class EmailChangeForm(forms.Form):
    new_email = forms.EmailField(
        required=True,
        label="New Email Address",
        widget=forms.EmailInput(attrs={'class': 'form-control', 'placeholder': 'Enter your new email address'})
    )
    current_password = forms.CharField(
        required=True,
        label="Current Password",
        widget=forms.PasswordInput(attrs={'class': 'form-control', 'placeholder': 'Enter your current password'})
    )

    def __init__(self, user, *args, **kwargs):
        self.user = user
        super().__init__(*args, **kwargs)

    def clean_new_email(self):
        new_email = self.cleaned_data.get('new_email')
        if User.objects.filter(email=new_email).exclude(id=self.user.id).exists():
            raise ValidationError("This email address is already in use.")
        return new_email

    def clean_current_password(self):
        current_password = self.cleaned_data.get('current_password')
        if current_password and not self.user.check_password(current_password):
            raise ValidationError("Incorrect current password.")
        return current_password
