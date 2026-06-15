from django.urls import path
from bakery import views

urlpatterns = [
    path('', views.index_view, name='index'),
    path('index.php', views.index_view, name='index_php'),
    path('aboutus.php', views.aboutus_view, name='aboutus'),
    path('signup.php', views.signup_view, name='signup'),
    path('login.php', views.login_view, name='login'),
    path('verify-mfa.php', views.verify_mfa, name='verify_mfa'),
    path('logout.php', views.logout_view, name='logout'),
    path('menu.php', views.menu_view, name='menu'),
    path('pickup.php', views.pickup_view, name='pickup'),
    path('delivery.php', views.pickup_view, name='delivery'),
    path('payment-success.php', views.payment_success_view, name='payment_success'),
    path('payment-success/', views.payment_success_view, name='payment_success_no_ext'),
    path('order-success.php', views.order_success_view, name='order_success'),
    path('receipt.php', views.receipt_view, name='receipt'),
    path('webhook/paymongo/', views.paymongo_webhook_view, name='paymongo_webhook'),
    path('set-password.php', views.set_password_view, name='set_password'),
    path('profile.php', views.profile_view, name='profile'),
    path('purchase-history.php', views.purchase_history_view, name='purchase_history'),
    path('orders/<str:order_reference>/', views.order_detail_view, name='order_detail'),
    path('change-password.php', views.change_password_view, name='change_password'),
    path('change-email.php', views.change_email_view, name='change_email'),
    
    # Staff Dashboard Routes
    path('staff/dashboard/', views.staff_dashboard, name='staff_dashboard'),
    path('staff/products/', views.staff_products, name='staff_products'),
    path('staff/products/create/', views.staff_product_create, name='staff_product_create'),
    path('staff/products/<int:product_id>/edit/', views.staff_product_edit, name='staff_product_edit'),
    path('staff/products/<int:product_id>/delete/', views.staff_product_delete, name='staff_product_delete'),
    path('staff/orders/', views.staff_orders, name='staff_orders'),
    path('staff/orders/<int:order_id>/', views.staff_order_detail, name='staff_order_detail'),
    path('staff/orders/<int:order_id>/move-to-processing/', views.move_to_processing, name='move_to_processing'),
    path('staff/orders/<int:order_id>/move-to-claimed/', views.move_to_claimed, name='move_to_claimed'),
    path('staff/orders/<int:order_id>/update-status/', views.update_order_status, name='update_order_status'),
    
    # Admin Staff Management Routes
    path('admin/staff/', views.admin_staff_list, name='admin_staff_list'),
    path('admin/staff/create/', views.admin_staff_create, name='admin_staff_create'),
    path('admin/staff/<int:user_id>/edit/', views.admin_staff_edit, name='admin_staff_edit'),
    path('admin/staff/<int:user_id>/delete/', views.admin_staff_delete, name='admin_staff_delete'),
    
    # Cart AJAX APIs mapped to match legacy PHP requests
    path('add-to-cart.php', views.cart_add, name='cart_add'),
    path('remove-from-cart.php', views.cart_remove, name='cart_remove'),
    path('update-cart-quantity.php', views.cart_update_quantity, name='cart_update_quantity'),
    path('get-cart.php', views.cart_get, name='cart_get'),
    path('checkout.php', views.checkout_view, name='checkout'),
    
    # MFA AJAX API
    path('toggle-mfa.php', views.toggle_mfa, name='toggle_mfa'),
    
    # CAPTCHA Route
    path('captcha.php', views.captcha_image_view, name='captcha_image'),
]
