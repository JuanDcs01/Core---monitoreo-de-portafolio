# urls.py
from django.urls import path
from . import views

urlpatterns = [
    path('dashboard/', views.index, name='index'),
    path('add_symbol/', views.add_holding, name='add_symbol'),
    path('delete_holding/', views.delete_holding, name='delete_holding'),
]