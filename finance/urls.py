from django.urls import path
from . import views

app_name = 'finance'

urlpatterns = [
    path('', views.finance_view, name='finance'),
    path('export-csv/', views.export_csv_view, name='export_csv'),
    path('regularize/', views.regularize_view, name='regularize'),
]
