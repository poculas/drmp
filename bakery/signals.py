from django.contrib.auth.signals import user_logged_in, user_logged_out
from django.dispatch import receiver
from django.db.models.signals import post_save
from django.contrib.auth.models import User
from .models import UserActivity, UserProfile

@receiver(user_logged_in)
def log_user_login(sender, request, user, **kwargs):
    ip_address = get_client_ip(request)
    UserActivity.objects.create(
        user=user,
        activity_type='login',
        ip_address=ip_address
    )

@receiver(user_logged_out)
def log_user_logout(sender, request, user, **kwargs):
    if user:
        ip_address = get_client_ip(request)
        UserActivity.objects.create(
            user=user,
            activity_type='logout',
            ip_address=ip_address
        )

@receiver(post_save, sender=User)
def create_user_profile(sender, instance, created, **kwargs):
    """Create UserProfile for new users (including OAuth users)"""
    if created:
        UserProfile.objects.get_or_create(
            user=instance,
            defaults={'contactnumber': '', 'role': 'customer'}
        )

def get_client_ip(request):
    x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
    if x_forwarded_for:
        ip = x_forwarded_for.split(',')[0]
    else:
        ip = request.META.get('REMOTE_ADDR')
    return ip
