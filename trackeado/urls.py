# urls.py
from django.urls import path
from . import views

urlpatterns = [
    path('dashboard/', views.dashboard, name='dashboard'),
    path('symbol/add/', views.add_holding, name='add_symbol'),
    path('holding/delete/', views.delete_holding, name='delete_holding'),
    path('watch_lists/', views.watch_lists, name='watch_lists'),
    path('watch_list_details/<str:watch_list>', views.watch_list_details, name='watch_list_details'),
    path('holding_list/add/', views.add_holding_list, name='add_holding_list'),
    path('holding_list/delete/', views.delete_holding_list, name='delete_holding_list'),
    path('watch_lists/delete/', views.delete_watch_lists, name='delete_watch_lists'),
    path('holding/search/', views.search_holding, name='search_holding'),
    path('holding/<str:symbol>/', views.holding, name='holding'),
    path('transaction/create/', views.create_transaction, name='create_transaction'),
]