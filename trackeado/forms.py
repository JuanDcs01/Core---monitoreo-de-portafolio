from .models import WatchList, WalletTransaction
from django import forms

class WatchListForm(forms.ModelForm):

    class Meta:

        model = WatchList

        fields = ['name']

class WalletTransactionForm(forms.ModelForm):

    class Meta:

        model = WalletTransaction

        exclude = ['user']

