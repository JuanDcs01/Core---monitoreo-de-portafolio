from .models import WatchList
from django.forms import models

class WatchListForm(models.ModelForm):

    class Meta:

        model = WatchList

        fields = ['name']
