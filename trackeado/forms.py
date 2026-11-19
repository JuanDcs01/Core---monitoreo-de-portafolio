from .models import WatchList, WalletTransaction, TransactionType, Trade, TradeType, Dividend
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

        exclude = ['wallet']

        widgets = {
            'date': forms.DateInput(
                format='%Y-%m-%d',
                attrs={
                    'class': 'form-control',
                    'type': 'date',
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
                    'class': 'form-control form-select'
                }
            )             
            }

    def __init__(self, *args, **kargs):
        super().__init__(*args, **kargs)
        options = [("", "Selecciona el tipo de tranferencia")] + list(TransactionType.choices)
        self.fields['type'].choices = options

class TradeForm(forms.ModelForm):

    class Meta:

        model = Trade

        exclude = ['user', 'user_holding']

        widgets = {
            'type': forms.Select(
                attrs={
                    'class': 'form-control form-select'
                }
            ),
            'shares': forms.NumberInput(
                attrs={
                    'class': 'form-control',
                    'placeholder': 'Cantidad de acciones'
                }
            ),
            'price': forms.NumberInput(
                attrs={
                    'class': 'form-control',
                    'placeholder': 'Precio'
                }
            ),
            'commission': forms.NumberInput(
                attrs={
                    'class': 'form-control',
                    'placeholder': 'Comisiones'
                }
            ),
            'date': forms.DateInput(
                format='%Y-%m-%d',
                attrs={
                    'class': 'form-control',
                    'type': 'date',
                },
            )
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        options = [("", "Selecciona el tipo de operación")] + list(TradeType.choices)
        self.fields["type"].choices = options

class DividendForm(forms.ModelForm):

    class Meta:
        model = Dividend

        exclude = ['user_holding', 'reinvested']

        widgets = {
            'net_amount': forms.NumberInput(attrs={
                'class': 'form-control',
                'placeholder': 'Monto'
            }),
            'commission': forms.NumberInput(attrs={
                'class': 'form-control',
                'placeholder': "Comisión"
            }),
            'date': forms.DateInput(
                format='%Y-%m-%d',
                attrs={
                    'class': 'form-control',
                    'type': 'date',
                },
            ),
        }