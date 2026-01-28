from django.urls import path
from . import views

urlpatterns = [
    path('', views.home, name='home'),

  path('product/<int:id>/', views.product_detail, name='product_detail'),


    path('login/', views.login_view, name='login'),
    path('register/', views.register_view, name='register'),
    path('logout/', views.logout_view, name='logout'),

    path('dashboard/', views.dashboard, name='dashboard'),
    path('dashboard/create/', views.product_create),
  path('dashboard/edit/<int:pk>/', views.dashboard_edit_product, name='dashboard_edit_product'),

   path('cart/remove/<int:product_id>/', views.remove_from_cart, name='remove_from_cart'),

    path('dashboard/delete/<int:pk>/', views.product_delete),

    path('cart/', views.cart_view, name='cart'),
    path('cart/add/<int:product_id>/', views.add_to_cart, name='add_to_cart'),
]
