from django.urls import path
from . import views

app_name = 'accounts'

urlpatterns = [
    path('register/', views.register_view, name='register'),
    path('login/', views.login_view, name='login'),
    path('logout/', views.logout_view, name='logout'),
    path('password-change/', views.password_change_view, name='password_change'),
    path('verify/<str:token>/', views.verify_email_view, name='verify_email'),
    path('verify-password/<str:token>/', views.verify_password_view, name='verify_password'),
    path('seller-profile/<int:user_id>/', views.seller_profile_view, name='seller_profile'),
]
