# urls.py
from django.urls import path
from .views import stock_dashboard
from . import views

urlpatterns = [
    path('dashboard/', stock_dashboard, name='stock_dashboard'),
    path('api/quote/<str:symbol>/', views.stock_quote, name='stock_quote')
]