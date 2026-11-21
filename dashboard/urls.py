from django.urls import path
from . import views

app_name = 'dashboard'

urlpatterns = [
    path('', views.overview_view, name='overview'),
    path('products/', views.products_view, name='products'),
    path('reviews/', views.reviews_view, name='reviews'),
    path('customers/', views.customers_view, name='customers'),
    path('settings/', views.settings_view, name='settings'),
]
