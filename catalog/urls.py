from django.urls import path
from . import views

app_name = 'catalog'

urlpatterns = [
    path('', views.product_list_view, name='product_list'),
    path('product/<int:pk>/', views.product_detail_view, name='product_detail'),
    path('product/new/', views.product_create_view, name='product_create'),
    path('product/<int:pk>/edit/', views.product_edit_view, name='product_edit'),
    path('product/<int:pk>/remove/', views.product_remove_view, name='product_remove'),
    path('calculate-frete/', views.calculate_frete_view, name='calculate_frete'),
]