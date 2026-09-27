# urls.py
from django.urls import path
from .views import stock_dashboard

urlpatterns = [
    path('dashboard/', stock_dashboard, name='stock_dashboard'),
]