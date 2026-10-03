from django.db import models
from users.models import User 

# Create your models here.

class Holding(models.Model):

    name = models.CharField(max_length=100, unique=True)
    symbol = models.CharField(max_length=10, unique=True)
    type = models.CharField(max_length=20)

    def __str__(self):
        return self.name

class UserHolding(models.Model):

    user = models.ForeignKey(User, on_delete=models.CASCADE)
    holding = models.ForeignKey(Holding, on_delete=models.CASCADE)

