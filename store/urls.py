from django.urls import path
from . import views

app_name = 'store'

urlpatterns = [
    # ========== HOME & PRODUCTS ==========
    path('', views.home, name='home'),
    path('product/<int:id>/', views.product_detail, name='product_detail'),
    path('product/search/', views.product_search, name='product_search'),

    # ========== AUTHENTICATION ==========
    path('login/', views.login_view, name='login'),
    path('register/', views.register_view, name='register'),
    path('logout/', views.logout_view, name='logout'),

    # ========== DASHBOARD (ADMIN) ==========
    path('dashboard/', views.dashboard, name='dashboard'),
    path('dashboard/create/', views.product_create, name='product_create'),
    path('dashboard/edit/<int:pk>/', views.dashboard_edit_product, name='dashboard_edit_product'),
    path('dashboard/delete/<int:pk>/', views.product_delete, name='product_delete'),

    # ========== CART & CHECKOUT ==========
    path('cart/', views.cart_view, name='cart_detail'),
    path('cart/add/<int:product_id>/', views.add_to_cart, name='add_to_cart'),
    path('cart/remove/<int:product_id>/', views.remove_from_cart, name='remove_from_cart'),
    path('checkout/', views.checkout, name='checkout'),

    # ========== WISHLIST & COMPARE ==========
    path('wishlist/', views.wishlist, name='wishlist'),
    path('wishlist/toggle/', views.wishlist_toggle, name='wishlist_toggle'),
    path('compare/', views.compare_view, name='compare'),

    # ========== USER PROFILE ==========
    path('profile/', views.profile, name='profile'),
    path('order-tracking/', views.order_tracking, name='order_tracking'),
    path('order-success/', views.order_success, name='order_success'),

    # ========== PLACEHOLDER URLS ==========
    # Các route dưới đây là placeholder để tránh lỗi template
    path('brand/add/', views.placeholder, name='brand_add'),
    path('brand/edit/', views.placeholder, name='brand_edit'),
    path('brand/delete/', views.placeholder, name='brand_delete'),
    path('user/detail/', views.placeholder, name='user_detail'),
    path('user/add/', views.placeholder, name='user_add'),
    path('user/edit/', views.placeholder, name='user_edit'),
    path('user/delete/', views.placeholder, name='user_delete'),
    path('product/add/', views.placeholder, name='product_add'),
    path('product/edit/', views.placeholder, name='product_edit'),
    path('product/specification/upload/', views.placeholder, name='product_specification_upload'),
    path('product/specification/delete/', views.placeholder, name='product_specification_delete'),
    path('qr-payment/list/', views.placeholder, name='qr_payment_list'),
    path('qr-payment/detail/', views.placeholder, name='qr_payment_detail'),
    path('qr-payment/approve/', views.placeholder, name='qr_payment_approve'),
    path('qr-payment/cancel/', views.placeholder, name='qr_payment_cancel'),
    path('admin/order/list/', views.placeholder, name='admin_order_list'),
    path('admin/order/detail/', views.placeholder, name='admin_order_detail'),
    path('admin/order/update-status/', views.placeholder, name='admin_order_update_status'),
    path('account/logout/', views.logout_view, name='account_logout'),
]
