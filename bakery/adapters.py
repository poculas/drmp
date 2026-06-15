# bakery/adapters.py
from allauth.socialaccount.adapter import DefaultSocialAccountAdapter
from allauth.exceptions import ImmediateHttpResponse
from allauth.account.models import EmailAddress
from django.contrib.auth import get_user_model
from django.shortcuts import redirect

User = get_user_model()

class MySocialAccountAdapter(DefaultSocialAccountAdapter):

    def pre_social_login(self, request, sociallogin):
        # Already connected to a social account, continue normally
        if sociallogin.is_existing:
            return

        # Get email from Google
        email = sociallogin.account.extra_data.get('email', '').lower()
        if not email:
            return

        # Check if a regular account exists with this email
        try:
            existing_user = User.objects.get(email__iexact=email)
            # Store sociallogin in session for use after confirmation
            request.session['pending_sociallogin'] = sociallogin.serialize()
            request.session['link_email'] = email
            raise ImmediateHttpResponse(redirect('link_account_prompt'))
        except User.DoesNotExist:
            pass