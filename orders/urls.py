from django.urls import path
from . import views

app_name = 'orders'

urlpatterns = [
    path('checkout/<int:product_id>/', views.checkout_view, name='checkout'),
    path('my-orders/', views.my_orders_view, name='my_orders'),
    path('tracking/<int:order_id>/', views.tracking_view, name='tracking'),
    path('review/<int:order_id>/', views.review_view, name='review'),
    path('confirm-receipt/<int:order_id>/', views.confirm_receipt_view, name='confirm_receipt'),
    path('refund/<int:order_id>/', views.refund_view, name='refund'),
    path('refund-status/<int:refund_id>/', views.refund_status_view, name='refund_status'),
    path('seller-orders/', views.seller_orders_view, name='seller_orders'),
    path('advance-status/<int:order_id>/', views.advance_status_view, name='advance_status'),
    path('refund-action/<int:refund_id>/<str:action>/', views.refund_action_view, name='refund_action'),
]
