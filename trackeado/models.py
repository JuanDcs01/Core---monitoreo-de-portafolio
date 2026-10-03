from django.db import models

# Create your models here.

class Holdings(models.Model):

    name = models.CharField(max_length=100, unique=True)
    symbol = models.CharField(max_length=10, unique=True)
    type = models.CharField(max_length=20)

    def __str__(self):
        return self.name

