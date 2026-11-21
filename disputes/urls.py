from django.urls import path
from . import views

app_name = 'disputes'

urlpatterns = [
    path('open/<int:order_id>/', views.open_dispute_view, name='open_dispute'),
    path('detail/<int:dispute_id>/', views.dispute_detail_view, name='dispute_detail'),
    path('mediation/', views.mediation_panel_view, name='mediation_panel'),
    path('mediation/<int:dispute_id>/', views.mediation_detail_view, name='mediation_detail'),
    path('seller-disputes/', views.seller_disputes_view, name='seller_disputes'),
    path('seller-dispute/<int:dispute_id>/', views.seller_dispute_detail_view, name='seller_dispute_detail'),
]
