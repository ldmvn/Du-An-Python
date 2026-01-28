from django.urls import path
from . import views

urlpatterns = [
    path('', views.home, name='home'),
    path('login/', views.login_view, name='login'),
    path('logout/', views.logout_view, name='logout'),
    path('dashboard/', views.dashboard, name='dashboard'),
    path('create/', views.product_create),
    path('update/<int:pk>/', views.product_update),
    path('delete/<int:pk>/', views.product_delete),
]
