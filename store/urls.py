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
    path('dashboard/admin/', views.dashboard, name='dashboard_admin'),
    path('dashboard/admin/products/', views.admin_products, name='admin_products'),
    path('dashboard/admin/orders/', views.admin_orders, name='admin_orders'),
    path('dashboard/create/', views.product_create, name='product_create'),
    path('dashboard/edit/<int:pk>/', views.dashboard_edit_product, name='dashboard_edit_product'),
    path('dashboard/edit/<int:pk>/media/', views.dashboard_edit_product_media, name='dashboard_edit_product_media'),
    path('dashboard/edit/<int:pk>/specs/', views.dashboard_edit_product_specs, name='dashboard_edit_product_specs'),
    path('dashboard/delete/<int:pk>/', views.product_delete, name='product_delete'),
    path('dashboard/categories/', views.category_list, name='category_list'),
    path('dashboard/categories/create/', views.category_create, name='category_create'),
    path('dashboard/categories/edit/<int:pk>/', views.category_edit, name='category_edit'),
    path('dashboard/categories/delete/<int:pk>/', views.category_delete, name='category_delete'),
    path('dashboard/users/', views.user_list, name='user_list'),
    path('dashboard/users/edit/<int:pk>/', views.user_edit, name='user_edit'),
    path('dashboard/users/delete/<int:pk>/', views.user_delete, name='user_delete'),

    # ========== CART & CHECKOUT ==========
    path('cart/', views.cart_view, name='cart_detail'),
    path('cart/add/<int:product_id>/', views.add_to_cart, name='add_to_cart'),
    path('cart/remove/<int:product_id>/', views.remove_from_cart, name='remove_from_cart'),
    path('cart/update/<int:product_id>/', views.update_cart_quantity, name='update_cart_quantity'),
    path('cart/clear/', views.clear_cart, name='clear_cart'),
    # AJAX endpoints
    path('ajax/cart/add/', views.add_to_cart_ajax, name='add_to_cart_ajax'),
    path('ajax/cart/update/', views.update_cart_quantity_ajax, name='update_cart_quantity_ajax'),
    path('ajax/cart/remove/', views.remove_from_cart_ajax, name='remove_from_cart_ajax'),
    path('checkout/', views.checkout, name='checkout'),
    path('checkout/cart/', views.checkout_from_cart, name='checkout_from_cart'),
    path('ajax/order/update-status/', views.update_order_status, name='update_order_status'),

    # ========== WISHLIST & COMPARE ==========
    path('wishlist/', views.wishlist, name='wishlist'),
    path('wishlist/toggle/', views.wishlist_toggle, name='wishlist_toggle'),
    # AJAX endpoint
    path('ajax/wishlist/toggle/', views.toggle_wishlist_ajax, name='toggle_wishlist_ajax'),
    path('compare/', views.compare_view, name='compare'),

    # ========== USER PROFILE ==========
    path('profile/', views.profile, name='profile'),
    path('order-tracking/', views.order_tracking, name='order_tracking'),
    path('order/<int:order_id>/', views.order_detail, name='order_detail'),
    path('order-tracking/cancel/<int:order_id>/', views.cancel_order, name='cancel_order'),
    path('order/delete/<int:order_id>/', views.delete_order, name='delete_order'),
    path('order-success/', views.order_success, name='order_success'),

    # ========== PLACEHOLDER URLS ==========
    # Các route dưới đây là placeholder để tránh lỗi template
    path('api/provinces/', views.get_provinces, name='get_provinces'),
    path('api/districts/<str:province_code>/', views.get_districts, name='get_districts'),
    path('api/wards/<str:district_code>/', views.get_wards, name='get_wards'),
    path('banner-images/list/', views.banner_list, name='banner_list'),
    path('banner-images/admin/', views.banner_admin_list, name='banner_admin_list'),
    path('banner-images/add/', views.banner_add, name='banner_add'),
    path('banner-images/import/', views.banner_import, name='banner_import'),
    path('banner-images/replace/', views.banner_replace, name='banner_replace'),
    path('banner-images/delete/', views.banner_delete, name='banner_delete'),
    path('banner-videos/admin/', views.video_banner_admin_list, name='video_banner_admin_list'),
    path('banner-videos/add/', views.video_banner_add, name='video_banner_add'),
    path('banner-videos/import/', views.video_banner_import, name='video_banner_import'),
    path('banner-videos/replace/', views.video_banner_replace, name='video_banner_replace'),
    path('banner-videos/delete/', views.video_banner_delete, name='video_banner_delete'),
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
