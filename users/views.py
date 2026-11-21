from django.contrib.auth.views import LoginView
from django.urls import reverse_lazy
from django.views.generic import CreateView, TemplateView
from .forms import (CustomRegisterForm, 
                    CustomLoginForm, 
                    CustomPasswordChangeForm, 
                    CustomPasswordResetConfirmForm, 
                    CustomPasswordResetForm,
                    CurrencyUpdateForm)
from django.shortcuts import redirect
from django.contrib.auth.views import (
    PasswordChangeView,
    PasswordResetView,
    PasswordResetDoneView,
    PasswordResetConfirmView,
    PasswordResetCompleteView,
)
from django.contrib.auth.mixins import LoginRequiredMixin
from trackeado.models import Wallet
from django.views.generic import UpdateView
from django.contrib.auth import get_user_model
from django.contrib import messages

User = get_user_model()

class RedirectAuthenticatedUserMixin:
    """Si el usuario ya está logueado, lo saca de esta vista."""
    redirect_authenticated_url = reverse_lazy('login')

    def dispatch(self, request, *args, **kwargs):
        if request.user.is_authenticated:
            return redirect(self.redirect_authenticated_url)
        return super().dispatch(request, *args, **kwargs)

class CustomLoginView(LoginView):
    form_class = CustomLoginForm
    template_name = 'registration/login.html'
    redirect_authenticated_user = True

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['title'] = 'Iniciar sesión'
        context['button'] = 'Entrar'
        return context

class CustomRegisterView(RedirectAuthenticatedUserMixin, CreateView):

    form_class = CustomRegisterForm
    template_name = 'registration/register.html'
    success_url = reverse_lazy('login')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['title'] = 'Registrarse'
        context['button'] = 'Registrarse'
        return context

    def form_valid(self, form):
        response = super().form_valid(form)

        Wallet.objects.create(user=self.object)

        return response

class CustomProfileView(LoginRequiredMixin, UpdateView):

    model = User
    form_class = CurrencyUpdateForm
    template_name = 'profile.html'
    login_url = reverse_lazy('login')
    success_url = reverse_lazy('profile')

    def get_object(self, queryset=None):
        return self.request.user

    def form_valid(self, form):
        response = super().form_valid(form)
        messages.success(self.request, "Moneda actualizada correctamente.")
        return response

    def form_invalid(self, form):
        messages.error(self.request, "No se pudo actualizar la moneda. Revisa la selección.")
        return super().form_invalid(form)

class CustomPasswordChangeView(PasswordChangeView):

    form_class = CustomPasswordChangeForm

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['title'] = 'Cambiar contraseña'
        context['button'] = 'Cambiar'
        return context

class CustomPasswordResetView(RedirectAuthenticatedUserMixin, PasswordResetView):

    form_class = CustomPasswordResetForm
    template_name = 'registration/password_reset_form.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['title'] = 'Restablecer contraseña'
        context['button'] = 'Continuar'
        return context

class CustomPasswordResetDoneView(RedirectAuthenticatedUserMixin, PasswordResetDoneView):

    template_name = 'registration/password_reset_done.html'

class CustomPasswordResetConfirmView(RedirectAuthenticatedUserMixin, PasswordResetConfirmView):

    form_class = CustomPasswordResetConfirmForm
    template_name = 'registration/password_reset_confirm.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['title'] = 'Nueva contraseña'
        context['button'] = 'Continuar'
        return context

class CustomPasswordResetCompleteView(RedirectAuthenticatedUserMixin, PasswordResetCompleteView):

    template_name = 'registration/password_reset_complete.html'