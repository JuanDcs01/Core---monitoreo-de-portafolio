from django.contrib.auth.forms import UserCreationForm
from django.contrib.auth.forms import AuthenticationForm
from django.contrib.auth.forms import PasswordChangeForm, PasswordResetForm, SetPasswordForm
from .models import User
from django import forms

class CustomRegisterForm(UserCreationForm):

    class Meta(UserCreationForm.Meta):

        model = User
        fields = UserCreationForm.Meta.fields + ('email',)

        widgets = {
            "username": forms.TextInput(attrs={
                "placeholder": "Usuario"
            }),
            "email":  forms.EmailInput(attrs={
                "placeholder":  "email"
            })
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.fields["username"].widget.attrs.update({
            "class": "form-control",
        })

        self.fields["email"].widget.attrs.update({
            "class": "form-control",
        })

        self.fields["password1"].widget.attrs.update({
            "placeholder": "Contraseña",
            "class": "form-control",
        })

        self.fields["password2"].widget.attrs.update({
            "placeholder": "Repita la contraseña",
            "class": "form-control",
        })

class CustomLoginForm(AuthenticationForm):

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.fields["username"].widget.attrs.update({
            "placeholder": "Usuario",
            "class": "form-control",
        })

        self.fields["password"].widget.attrs.update({
            "placeholder": "Contraseña",
            "class": "form-control",
        })

class CustomPasswordChangeForm(PasswordChangeForm):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.fields["old_password"].widget.attrs.update({
            "placeholder": "Contraseña actual",
            "class": "form-control",
        })
        self.fields["new_password1"].widget.attrs.update({
            "placeholder": "Nueva contraseña",
            "class": "form-control",
        })
        self.fields["new_password2"].widget.attrs.update({
            "placeholder": "Repite la contraseña",
            "class": "form-control",
        })

class CustomPasswordResetForm(PasswordResetForm):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.fields["email"].widget.attrs.update({
            "placeholder": "Correo electrónico",
            "class": "form-control",
        })

class CustomPasswordResetConfirmForm(SetPasswordForm):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.fields["new_password1"].widget.attrs.update({
            "placeholder": "Nueva contraseña",
            "class": "form-control",
        })
        self.fields["new_password2"].widget.attrs.update({
            "placeholder": "Repite la contraseña",
            "class": "form-control",
        })