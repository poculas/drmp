from django.urls import path
from bakery import views

urlpatterns = [
    path('', views.index_view, name='index'),
    path('index.php', views.index_view, name='index_php'),
    path('aboutus.php', views.aboutus_view, name='aboutus'),
    path('signup.php', views.signup_view, name='signup'),
    path('login.php', views.login_view, name='login'),
    path('logout.php', views.logout_view, name='logout'),
    path('menu.php', views.menu_view, name='menu'),
    path('delivery.php', views.delivery_view, name='delivery'),
    path('receipt.php', views.receipt_view, name='receipt'),
    
    # Cart AJAX APIs mapped to match legacy PHP requests
    path('add-to-cart.php', views.cart_add, name='cart_add'),
    path('remove-from-cart.php', views.cart_remove, name='cart_remove'),
    path('get-cart.php', views.cart_get, name='cart_get'),
    path('checkout.php', views.checkout_view, name='checkout'),
]
