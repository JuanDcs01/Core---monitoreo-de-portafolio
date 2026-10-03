from django.urls import path
from . import views
from django.contrib.auth.views import LogoutView, PasswordChangeDoneView

urlpatterns = [
    path('profile/', views.CustomProfileView.as_view(), name='profile'),
    path("login/", views.CustomLoginView.as_view(), name="login"),
    path("logout/", LogoutView.as_view(), name="logout"),
    path("register/", views.CustomRegisterView.as_view(), name="register"),
    # Cambiar contraseña
    path('password_change/', views.CustomPasswordChangeView.as_view(), name='password_change'),
    path('password_change_done/', PasswordChangeDoneView.as_view(), name='password_change_done'),
    # Recuperar contraseña
    path('password_reset/', views.CustomPasswordResetView.as_view(), name='password_reset'),
    path('password_reset/done/', views.CustomPasswordResetDoneView.as_view(), name='password_reset_done'),
    path('reset/<uidb64>/<token>/', views.CustomPasswordResetConfirmView.as_view(), name='password_reset_confirm'),
    path('reset/done/', views.CustomPasswordResetCompleteView.as_view(), name='password_reset_complete'),
]