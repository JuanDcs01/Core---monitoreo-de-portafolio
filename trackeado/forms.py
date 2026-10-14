from .models import WatchList, WalletTransaction
from django import forms

class WatchListForm(forms.ModelForm):

    class Meta:

        model = WatchList

        fields = ['name']

        widgets = {
            'name': forms.TextInput(
                attrs={
                    'class': 'form-control',
                    'placeholder': 'Nombre de la lista'
                }
            )
        }

class WalletTransactionForm(forms.ModelForm):

    class Meta:

        model = WalletTransaction

        exclude = ['user']

        widgets = {
            'date': forms.DateInput(
                format='%Y-%m-%d',
                attrs={
                    'class': 'form-control',
                    'type': 'date',  # Clave para el selector nativo HTML5
                },
            ),
            'commission': forms.NumberInput(
                attrs={
                    'class': 'form-control',
                    'placeholder': 'comisión'
                }
            ),
            'net_amount': forms.NumberInput(
                attrs={
                    'class': 'form-control',
                    'placeholder': 'monto'
                }
            ),
            'type': forms.Select(
                attrs={
                    'class': 'form-select'
                }
            )             
            }